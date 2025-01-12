import bcrypt
import pymysql
from dotenv import load_dotenv, find_dotenv
import os
import re

# Загружаем переменные окружения из .env файла
load_dotenv(find_dotenv())

class MySQL:
    def __init__(self, host, port, user, password, db_name):
        """
        Инициализация подключения к базе данных MySQL
        """
        self.connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )

    def create_users_table(self):
        """
        Создание таблицы пользователей, если она еще не существует.
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS `users` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_table_query)
                self.connection.commit()
                print("Таблица 'users' успешно создана.")
        except pymysql.MySQLError as e:
            print(f"Ошибка при создании таблицы: {e}")

    def get_user_id_by_email(self, email):
        """
        Получить ID пользователя по email.
        """
        query = "SELECT id FROM `users` WHERE email = %s"
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (email,))
                result = cursor.fetchone()
                if result:
                    return result['id']
                else:
                    print(f"Пользователь с email {email} не найден.")
                    return None
        except pymysql.MySQLError as e:
            print(f"Ошибка при получении id пользователя: {e}")
            return None

    def hash_password(self, password):
        """
        Хэширование пароля с использованием bcrypt.
        """
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password

    def add_user(self, email, password):
        """
        Добавить нового пользователя в базу данных.
        """
        # Проверка формата email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            print("Неверный формат email.")
            return False

        hashed_password = self.hash_password(password)
        check_query = "SELECT COUNT(*) AS count FROM `users` WHERE email = %s"
        insert_query = "INSERT INTO `users` (email, password) VALUES (%s, %s)"
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(check_query, (email,))
                result = cursor.fetchone()
                if result['count'] > 0:
                    print(f"Пользователь с email {email} уже существует.")
                    return False
                cursor.execute(insert_query, (email, hashed_password))
                self.connection.commit()
                print("Пользователь успешно добавлен.")
                return True
        except pymysql.MySQLError as e:
            print(f"Ошибка при добавлении пользователя: {e}")
            return False

    def verify_password(self, email, password):
        """
        Проверка пароля пользователя.
        """
        query = "SELECT password FROM `users` WHERE email = %s"
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (email,))
                result = cursor.fetchone()
                if result:
                    stored_password = result['password'].encode('utf-8')
                    if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                        print("Пароль верный.")
                        return True
                    else:
                        print("Неверный пароль.")
                        return False
                else:
                    print("Пользователь с таким email не найден.")
                    return False
        except pymysql.MySQLError as e:
            print(f"Ошибка при проверке пароля: {e}")
            return False

    def get_user_info(self, user_id):
        """
        Получить информацию о пользователе по его ID.
        """
        query = "SELECT email, created_at FROM `users` WHERE id = %s"
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()
                if result:
                    print(f"Информация о пользователе: {result}")
                    return result
                else:
                    print(f"Пользователь с ID {user_id} не найден.")
                    return None
        except pymysql.MySQLError as e:
            print(f"Ошибка при получении информации о пользователе: {e}")
            return None

    def del_user(self, user_id):
        """
        Удалить пользователя по ID.
        """
        query = "DELETE FROM `users` WHERE id = %s"
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, (user_id,))
            self.connection.commit()
            print(f"Пользователь с ID {user_id} удален.")
        except pymysql.MySQLError as e:
            print(f"Ошибка при удалении пользователя: {e}")

    @staticmethod
    def check_password_strength(password):
        """
        Проверить надежность пароля.
        """
        min_length = 8
        if len(password) < min_length:
            return False, "Пароль должен содержать хотя бы 8 символов."
        if not re.search(r'[A-Z]', password):
            return False, "Пароль должен содержать хотя бы одну заглавную букву."
        if not re.search(r'[a-z]', password):
            return False, "Пароль должен содержать хотя бы одну строчную букву."
        if not re.search(r'[0-9]', password):
            return False, "Пароль должен содержать хотя бы одну цифру."
        if not re.search(r'[\W_]', password):
            return False, "Пароль должен содержать хотя бы один специальный символ (например, !, @, #, $, %, ^)."
        if ' ' in password:
            return False, "Пароль не должен содержать пробелы."
        return True, "Пароль надежен."
