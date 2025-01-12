import io
import os
from datetime import date, datetime, timedelta
import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from scipy.stats import gaussian_kde
from dotenv import load_dotenv, find_dotenv
from DB import MySQL
import pandas as pd
import openpyxl
from io import BytesIO


# Функция для создания Excel файла
def create_excel_file(data, mean, median, metal_choice=None, currency_group=None):
    # Создаем DataFrame для данных
    if metal_choice:
        df = pd.DataFrame({
            "Дата": data["dates"],
            "Цена": data["values"]
        })
    elif currency_group:
        df = pd.DataFrame({
            "Дата": data["dates"],
            "Курс": data["rates"]
        })

    # Добавляем статистику в отдельный DataFrame
    stats_df = pd.DataFrame({
        "Статистика": ["Среднее арифметическое", "Медиана"],
        "Значение": [mean, median]
    })

    # Запись в Excel файл
    with io.BytesIO() as output:
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Данные", index=False)
            stats_df.to_excel(writer, sheet_name="Статистика", index=False)
            writer.save()

        excel_data = output.getvalue()

    return excel_data

# Функция для формирования Excel файла с данными и графиками
def create_excel_with_charts(dates, values, statistics, file_name="metal_prices_report.xlsx"):
    # Создание DataFrame с данными
    df = pd.DataFrame({
        'Дата': dates,
        'Цена': values
    })

    # Создание Excel файла
    with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
        # Запись данных в Excel
        df.to_excel(writer, sheet_name='Data', index=False)

        # Получение книги и листа
        workbook = writer.book
        worksheet = writer.sheets['Data']

        # Добавление статистики в новый лист
        stats_worksheet = workbook.add_worksheet('Statistics')
        stats_worksheet.write('A1', 'Медиана')
        stats_worksheet.write('B1', statistics['median'])
        stats_worksheet.write('A2', 'Среднее арифметическое')
        stats_worksheet.write('B2', statistics['mean'])
        stats_worksheet.write('A3', 'Максимум')
        stats_worksheet.write('B3', statistics['maximum'])
        stats_worksheet.write('A4', 'Минимум')
        stats_worksheet.write('B4', statistics['minimum'])

        # Построение графиков с помощью XlsxWriter
        chart = workbook.add_chart({'type': 'line'})
        chart.add_series({
            'name': 'Цена',
            'categories': f'=Data!$A$2:$A${len(dates) + 1}',
            'values': f'=Data!$B$2:$B${len(values) + 1}'
        })
        chart.set_title({'name': 'График цен'})
        chart.set_x_axis({'name': 'Дата'})
        chart.set_y_axis({'name': 'Цена (BYN)'})
        worksheet.insert_chart('D2', chart)

        # Сохранение Excel файла в буфер
        writer.save()

    # Чтение в бинарном формате для отправки в Streamlit
    with open(file_name, 'rb') as f:
        file_data = f.read()

    # Отправка в Streamlit
    st.download_button(
        label="Скачать отчет в формате Excel",
        data=file_data,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# Пример вызова функции с данными
def save_and_export_data(dates, values):
    # Вычисление статистики
    median = np.median(values)
    mean = np.mean(values)
    maximum = np.max(values)
    minimum = np.min(values)

    # Формирование статистики
    statistics = {
        'median': median,
        'mean': mean,
        'maximum': maximum,
        'minimum': minimum
    }

    # Создание Excel файла с данными и графиками
    create_excel_with_charts(dates, values, statistics)


# Вспомогательная функция для разделения диапазона дат
def split_date_range(start_date, end_date, max_days=365):
    current_date = start_date
    while current_date < end_date:
        next_date = min(current_date + timedelta(days=max_days), end_date)
        yield current_date, next_date
        current_date = next_date

# Вспомогательная функция для получения данных из API в пределах ограничений
def fetch_data_in_chunks(api_url, start_date, end_date, data_key):
    all_data = []
    for chunk_start, chunk_end in split_date_range(start_date, end_date):
        params = {"startDate": chunk_start.isoformat(), "endDate": chunk_end.isoformat()}
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                all_data.extend(data)
        else:
            st.error(f"Ошибка при запросе данных: {response.status_code}")
            break
    return all_data

# Обработка данных до 1 июля 2016 года
def process_data_before_2016(data, value_key):
    threshold_date = datetime(2016, 7, 1)
    for item in data:
        date_obj = datetime.strptime(item['Date'][:10], '%Y-%m-%d')
        if date_obj < threshold_date:
            item[value_key] /= 10000
    return data

# Получение ближайшей доступной цены
def get_nearest_price(api_url, value_key):
    today = date.today()
    delta = timedelta(days=1)

    for offset in range(7):
        check_date = today - delta * offset
        params = {"startDate": check_date.isoformat(), "endDate": check_date.isoformat()}
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0][value_key]
    return None

# Построение графика цен на металлы
def get_metal_price(metal_choice, start_date, end_date):
    metal_urls = {
        "Золото": "https://api.nbrb.by/bankingots/prices/0",
        "Серебро": "https://api.nbrb.by/bankingots/prices/1",
        "Платина": "https://api.nbrb.by/bankingots/prices/2",
        "Палладий": "https://api.nbrb.by/bankingots/prices/3"
    }
    url = metal_urls[metal_choice]
    data = fetch_data_in_chunks(url, start_date, end_date, data_key="Value")
    if data:
        data = process_data_before_2016(data, "Value")
        dates = [datetime.strptime(item['Date'][:10], '%Y-%m-%d') for item in data]
        values = [item['Value'] for item in data]

        # Построение графика
        plt.figure(figsize=(12, 6))
        plt.plot(dates, values, marker='o', linestyle='-', color='b', label=f"Цена {metal_choice}")
        plt.title(f"График цен {metal_choice} ({start_date} - {end_date})", fontsize=16)
        plt.xlabel("Дата", fontsize=14)
        plt.ylabel("Цена (за грамм)", fontsize=14)
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=12)
        plt.tight_layout()
        st.pyplot(plt)

        # Дополнительный анализ данных
        display_statistics(values, f"{metal_choice} (цены)")
    else:
        st.error(f"Данные о {metal_choice} отсутствуют.")

# Построение графика курса валют
def get_currency_data(api_url, start_date, end_date):
    data = fetch_data_in_chunks(api_url, start_date, end_date, data_key="Cur_OfficialRate")
    if data:
        data = process_data_before_2016(data, "Cur_OfficialRate")
        dates = [datetime.strptime(item['Date'][:10], '%Y-%m-%d') for item in data]
        rates = [item['Cur_OfficialRate'] for item in data]

        # Построение графика
        plt.figure(figsize=(12, 6))
        plt.plot(dates, rates, marker='o', linestyle='-', color='g', label="Курс валюты")
        plt.title("График курса валют", fontsize=16)
        plt.xlabel("Дата", fontsize=14)
        plt.ylabel("Курс (BYN)", fontsize=14)
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.xticks(rotation=45)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=12)
        plt.tight_layout()
        st.pyplot(plt)

        # Дополнительный анализ данных
        display_statistics(rates, "Курс валюты")
    else:
        st.error("Данные отсутствуют для выбранного периода.")

# Вычисление статистики и построение гистограммы/плотности вероятности
def display_statistics(values, label):
    mean_value = np.mean(values)
    median_value = np.median(values)
    maximum = np.max(values)
    minimum = np.min(values)
    st.write(f"### Статистика для {label}")
    st.write(f"Среднее арифметическое: {mean_value:.2f}")
    st.write(f"Медиана: {median_value:.2f}")
    st.write(f"Максимум: {maximum:.2f}")
    st.write(f"Минимум: {minimum:.2f}")

    # Построение гистограммы
    plt.figure(figsize=(8, 4))
    plt.hist(values, bins=20, color='c', alpha=0.7, edgecolor='k', label='Гистограмма')
    plt.title(f"Гистограмма {label}", fontsize=14)
    plt.xlabel("Значение", fontsize=12)
    plt.ylabel("Частота", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    st.pyplot(plt)

    # Оценка плотности вероятности
    density = gaussian_kde(values)
    x_vals = np.linspace(min(values), max(values), 1000)
    plt.figure(figsize=(8, 4))
    plt.plot(x_vals, density(x_vals), color='r', label='Плотность вероятности')
    plt.title(f"Плотность вероятности {label}", fontsize=14)
    plt.xlabel("Значение", fontsize=12)
    plt.ylabel("Плотность", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    st.pyplot(plt)

# Отображение текущей цены металла или валюты
def display_current_price(metal_choice=None, currency_group=None):
    if metal_choice:
        metal_urls = {
            "Золото": "https://api.nbrb.by/bankingots/prices/0",
            "Серебро": "https://api.nbrb.by/bankingots/prices/1",
            "Платина": "https://api.nbrb.by/bankingots/prices/2",
            "Палладий": "https://api.nbrb.by/bankingots/prices/3",
        }
        url = metal_urls[metal_choice]
        current_price = get_nearest_price(url, "Value")
        if current_price is not None:
            st.metric(label=f"Цена {metal_choice} на ближайший доступный день", value=f"{current_price:.2f} BYN")
        else:
            st.error("Не удалось получить текущую цену.")
    elif currency_group:
        api_urls = {
            "Доллары (USD)": "https://api.nbrb.by/exrates/rates/dynamics/431",
            "Евро (EUR)": "https://api.nbrb.by/exrates/rates/dynamics/451",
            "Российские рубли (RUB)": "https://api.nbrb.by/exrates/rates/dynamics/456",
        }
        url = api_urls[currency_group]
        current_price = get_nearest_price(url, "Cur_OfficialRate")
        if current_price is not None:
            st.metric(label=f"Курс {currency_group} на ближайший доступный день", value=f"{current_price:.2f} BYN")
        else:
            st.error("Не удалось получить текущий курс.")

def display_closest_price(metal_choice=None, currency_group=None):
    """
    Отображает ближайшую доступную цену для выбранного металла или валюты.
    Если цена на сегодня недоступна, ищет ближайшую дату с доступными данными.
    """
    today = date.today()

    if metal_choice:
        metal_urls = {
            "Золото": "https://api.nbrb.by/bankingots/prices/0",
            "Серебро": "https://api.nbrb.by/bankingots/prices/1",
            "Платина": "https://api.nbrb.by/bankingots/prices/2",
            "Палладий": "https://api.nbrb.by/bankingots/prices/3",
        }
        url = metal_urls[metal_choice]
    elif currency_group:
        api_urls = {
            "Доллары (USD)": "https://api.nbrb.by/exrates/rates/dynamics/431",
            "Евро (EUR)": "https://api.nbrb.by/exrates/rates/dynamics/451",
            "Российские рубли (RUB)": "https://api.nbrb.by/exrates/rates/dynamics/456",
        }
        url = api_urls[currency_group]
    else:
        return

    current_date = today

    while True:
        response = requests.get(url, params={"startDate": current_date.isoformat(), "endDate": current_date.isoformat()})
        if response.status_code == 200:
            data = response.json()
            if data:
                price_key = "Value" if metal_choice else "Cur_OfficialRate"
                st.metric(label=f"Цена {metal_choice or currency_group} на {current_date}", value=f"{data[0][price_key]:.2f} BYN")
                return
        current_date -= timedelta(days=1)

        if current_date < today - timedelta(days=30):
            st.error("Не удалось получить данные за последние 30 дней.")
            return


def plot_histogram(data, title="Гистограмма", xlabel="Значение", ylabel="Частота"):
    """Строит гистограмму данных."""
    plt.figure(figsize=(10, 6))
    plt.hist(data, bins=20, color="skyblue", edgecolor="black", alpha=0.7)
    plt.title(title, fontsize=16)
    plt.xlabel(xlabel, fontsize=14)
    plt.ylabel(ylabel, fontsize=14)
    plt.grid(alpha=0.3)
    st.pyplot(plt)


def plot_density(data, title="Плотность вероятности", xlabel="Значение", ylabel="Плотность"):
    """Строит график плотности вероятности."""
    plt.figure(figsize=(10, 6))
    density = gaussian_kde(data)
    x = np.linspace(min(data), max(data), 1000)
    plt.plot(x, density(x), color="blue", label="Плотность вероятности")
    plt.fill_between(x, density(x), color="blue", alpha=0.3)
    plt.title(title, fontsize=16)
    plt.xlabel(xlabel, fontsize=14)
    plt.ylabel(ylabel, fontsize=14)
    plt.grid(alpha=0.3)
    plt.legend()
    st.pyplot(plt)


def calculate_statistics(data):
    """Вычисляет медиану, среднее арифметическое, максимум и минимум, возвращает их в удобном формате."""
    median = np.median(data)
    mean = np.mean(data)
    maximum = np.max(data)
    minimum = np.min(data)

    st.write(f"**Медиана:** {median:.2f}")
    st.write(f"**Среднее арифметическое:** {mean:.2f}")
    st.write(f"**Максимум:** {maximum:.2f}")
    st.write(f"**Минимум:** {minimum:.2f}")

    return median, mean, maximum, minimum
