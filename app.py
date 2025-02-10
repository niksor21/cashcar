import logging
from flask import Flask, send_from_directory, request, redirect
import os
from db import initialize_db, add_request, get_all_requests

# Настраиваем логирование: уровень DEBUG, формат с датой/временем.
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)

app = Flask(__name__, static_folder='static', static_url_path='')

# Инициализация базы данных
initialize_db()


@app.route('/')
def index():
    app.logger.debug("Открываем главную страницу (/)")  # Пример отладочного сообщения
    return app.send_static_file('index.html')


# Специальный маршрут для /images
@app.route('/images/<path:filename>')
def serve_images(filename):
    images_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images')
    app.logger.debug(f"Запрошено изображение: /images/{filename}")
    return send_from_directory(images_path, filename)


@app.route('/save', methods=['POST'])
def save():
    # Считываем данные формы
    fullname = request.form.get('fullname')
    email = request.form.get('email')
    phone = request.form.get('phone')
    subject = request.form.get('subject')
    message = request.form.get('message')

    app.logger.info(f"Получены данные формы: fullname={fullname}, email={email}, "
                    f"phone={phone}, subject={subject}, message={message}")

    # Добавляем данные в базу
    add_request(fullname, email, phone, subject, message)

    app.logger.info("Данные успешно сохранены в базу. Перенаправляем на главную.")
    return redirect('/?success=1')


if __name__ == '__main__':
    app.run(debug=False)
