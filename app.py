import logging
from flask import Flask, send_from_directory, request, redirect
import os
import sqlite3
from datetime import datetime

# Настраиваем логирование: уровень DEBUG, формат с датой/временем.
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

app = Flask(__name__, static_folder='static', static_url_path='')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@app.route('/')
def index():
    app.logger.debug("Открываем главную страницу (/)")  # Пример отладочного сообщения
    return app.send_static_file('index.html')

# Специальный маршрут для /images
@app.route('/images/<path:filename>')
def serve_images(filename):
    images_path = os.path.join(BASE_DIR, 'images')
    app.logger.debug(f"Запрошено изображение: /images/{filename}")
    return send_from_directory(images_path, filename)

@app.route('/save', methods=['POST'])
def save():
    # Считываем данные формы
    fullname = request.form.get('fullname')
    email    = request.form.get('email')
    phone    = request.form.get('phone')
    subject  = request.form.get('subject')
    message  = request.form.get('message')

    app.logger.info(f"Получены данные формы: fullname={fullname}, email={email}, "
                    f"phone={phone}, subject={subject}, message={message}")

    # Подключаемся к БД (или создаём, если нет файла)
    db_path = os.path.join(BASE_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Создаём таблицу, если ещё не существует, добавляем поле для времени
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            email TEXT,
            phone TEXT,
            subject TEXT,
            message TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Получаем текущее время
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Вставляем данные с временной меткой
    cursor.execute('''
        INSERT INTO contacts (fullname, email, phone, subject, message, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (fullname, email, phone, subject, message, timestamp))

    conn.commit()
    conn.close()

    app.logger.info("Данные успешно сохранены в базу. Перенаправляем на главную.")
    return redirect('/?success=1')

if __name__ == '__main__':
    app.run(debug=True)
