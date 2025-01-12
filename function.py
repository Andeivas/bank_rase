import re

def check_password_strength(password):
    strength = 0

    # Проверка длины пароля
    if len(password) >= 8:
        strength += 20

    # Проверка на наличие заглавной буквы
    if re.search(r'[A-Z]', password):
        strength += 20

    # Проверка на наличие строчной буквы
    if re.search(r'[a-z]', password):
        strength += 20

    # Проверка на наличие цифры
    if re.search(r'[0-9]', password):
        strength += 20

    # Проверка на наличие специального символа
    if re.search(r'[\W_]', password):
        strength += 20

    # Проверка на отсутствие пробела
    if ' ' not in password:
        strength += 10

    return strength