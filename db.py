import sqlite3
import os
from datetime import datetime

# Путь к базе данных
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

# Функция для получения подключения к базе данных
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # чтобы можно было обращаться к столбцам по именам
    return conn

# Проверяем существование файла БД и создаём, если его нет
def initialize_db():
    # Создаём соединение с базой данных (файл создастся, если его нет)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Создаём таблицу contacts с дополнительными полями status и executor
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            email TEXT,
            phone TEXT,
            subject TEXT,
            message TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'new',       -- Статус заявки, по умолчанию "new" (новая)
            executor TEXT DEFAULT ''         -- Имя исполнителя, по умолчанию пустое
        )
    ''')

    conn.commit()
    conn.close()

# Функция для добавления новой заявки в базу данных
def add_request(fullname, email, phone, subject, message):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Получаем текущее время
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Вставляем данные. Поля status и executor будут установлены по умолчанию ('new' и пустое значение)
    cursor.execute('''
        INSERT INTO contacts (fullname, email, phone, subject, message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (fullname, email, phone, subject, message, timestamp))

    conn.commit()
    conn.close()

# Функция для получения всех заявок из базы данных
def get_all_requests():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM contacts")
    requests = cursor.fetchall()

    conn.close()
    return requests

# Функция для обновления статуса заявки
def update_status(request_id, status, executor=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE contacts
        SET status = ?, executor = ?
        WHERE id = ?
    ''', (status, executor, request_id))

    conn.commit()
    conn.close()

def get_request_by_id(request_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM contacts WHERE id = ?", (request_id,))
    req = cursor.fetchone()
    conn.close()
    return req

# При запуске модуля напрямую инициализируем базу
if __name__ == '__main__':
    initialize_db()
