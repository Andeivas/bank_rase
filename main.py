import os
from datetime import date
import streamlit as st
from dotenv import load_dotenv, find_dotenv
from DB import MySQL
from API import (
    get_metal_price,
    get_currency_data,
    display_closest_price,
    plot_histogram,
    plot_density,
    calculate_statistics,
    create_excel_file
)
import pandas as pd
import io

# Загрузка переменных окружения
load_dotenv(find_dotenv())

# Подключение к базе данных
bd = MySQL(
    host=os.getenv("host"),
    port=3306,
    user=os.getenv("user"),
    password=os.getenv("password"),
    db_name=os.getenv("database"),
)

# Инициализация состояний
if 'form_state' not in st.session_state:
    st.session_state.form_state = 'login'

if 'metal_choice' not in st.session_state:
    st.session_state.metal_choice = None

if 'menu_choice' not in st.session_state:
    st.session_state.menu_choice = 'Металл'

# Боковое меню с кнопками
if st.session_state.form_state != 'login':
    with st.sidebar:
        if st.button("Металл", use_container_width=True):
            st.session_state.menu_choice = "Металл"
            st.session_state.form_state = 'metal_analytics'

        if st.button("Валюта", use_container_width=True):
            st.session_state.menu_choice = "Валюта"
            st.session_state.form_state = 'currency_analytics'

        if st.button("Личный кабинет", use_container_width=True):
            st.session_state.menu_choice = "Личный кабинет"
            st.session_state.form_state = 'profile'

        if st.button("Выход", use_container_width=True):
            st.session_state.menu_choice = "Выход"
            st.session_state.form_state = 'login'
            st.session_state.metal_choice = None
            st.session_state.menu_choice = 'Металл'

# Обработка форм
if st.session_state.form_state == 'login':
    with st.form("login"):
        st.markdown("#### Введите свои данные для входа")
        email = st.text_input("Email")
        password = st.text_input("Пароль", type="password")
        submit = st.form_submit_button("Войти")
        register = st.form_submit_button("Регистрация")

    if submit:
        if bd.verify_password(email, password):
            st.session_state.form_state = 'analytics'
            st.success("Вход выполнен успешно")
        else:
            st.error("Ошибка входа. Неверный email или пароль.")

    if register:
        st.session_state.form_state = 'registration'

elif st.session_state.form_state == 'registration':
    with st.form("registration"):
        st.markdown("#### Создайте новый аккаунт")
        email = st.text_input("Email")
        password = st.text_input("Пароль", type="password")
        password_repeat = st.text_input("Подтвердите пароль", type="password")
        submit = st.form_submit_button("Зарегистрироваться")

    if submit:
        if password == password_repeat:
            if bd.get_user_id_by_email(email):
                st.error(f"Пользователь с email {email} уже существует.")
            else:
                if bd.add_user(email, password):
                    st.success("Регистрация прошла успешно!")
                    st.session_state.form_state = 'login'
                else:
                    st.error("Ошибка при регистрации.")
        else:
            st.error("Пароли не совпадают.")

elif st.session_state.form_state == 'profile':
    st.markdown("### Личный кабинет")
    st.write("Здесь будет информация о вашем профиле и настройки.")

elif st.session_state.form_state == 'metal_analytics':
    st.markdown("### Анализ цен на драгоценные металлы")

    metal_choice = st.radio("Выберите металл:", ("Золото", "Серебро", "Платина", "Палладий"))
    display_closest_price(metal_choice=metal_choice)

    start_date = st.date_input("Выберите начальную дату:", date.today())
    end_date = st.date_input("Выберите конечную дату:", date.today())

    if st.button("Показать данные"):
        st.markdown(f"#### Данные для {metal_choice} с {start_date} по {end_date}")
        data = get_metal_price(metal_choice, start_date, end_date)

        if data:
            st.markdown("### Гистограмма цен")
            plot_histogram(data, label=f"Цена {metal_choice}")

            st.markdown("### Плотность вероятности")
            plot_density(data, label=f"Цена {metal_choice}")

            mean, median = calculate_statistics(data)
            st.metric(label="Среднее арифметическое", value=f"{mean:.2f}")
            st.metric(label="Медиана", value=f"{median:.2f}")

            # Создание Excel файла
            excel_data = create_excel_file(data, mean, median, metal_choice=metal_choice)

            # Кнопка для скачивания Excel файла
            st.download_button(
                label="Скачать Excel файл",
                data=excel_data,
                file_name=f"{metal_choice}_данные_с_{start_date}_по_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

elif st.session_state.form_state == 'currency_analytics':
    st.markdown("### Анализ курсов валют")

    currency_group = st.radio("Выберите категорию валюты:",
                              ("Доллары (USD)", "Евро (EUR)", "Российские рубли (RUB)"), index=0)

    display_closest_price(currency_group=currency_group)

    api_urls = {
        "Доллары (USD)": "https://api.nbrb.by/exrates/rates/dynamics/431",
        "Евро (EUR)": "https://api.nbrb.by/exrates/rates/dynamics/451",
        "Российские рубли (RUB)": "https://api.nbrb.by/exrates/rates/dynamics/456",
    }

    selected_url = api_urls[currency_group]
    start_date = st.date_input("Начальная дата:", date.today())
    end_date = st.date_input("Конечная дата:", date.today())

    if st.button("Показать данные"):
        st.markdown(f"#### Данные для {currency_group} с {start_date} по {end_date}")
        data = get_currency_data(selected_url, start_date, end_date)

        if data:
            st.markdown("### Гистограмма курсов")
            plot_histogram(data, label=f"Курс {currency_group}")

            st.markdown("### Плотность вероятности")
            plot_density(data, label=f"Курс {currency_group}")

            mean, median = calculate_statistics(data)
            st.metric(label="Среднее арифметическое", value=f"{mean:.2f}")
            st.metric(label="Медиана", value=f"{median:.2f}")

            # Создание Excel файла
            excel_data = create_excel_file(data, mean, median, currency_group=currency_group)

            # Кнопка для скачивания Excel файла
            st.download_button(
                label="Скачать Excel файл",
                data=excel_data,
                file_name=f"{currency_group}_данные_с_{start_date}_по_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )



