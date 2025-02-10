import telebot
from telebot import types
import time
import threading
from db import get_all_requests, update_status, get_request_by_id  # Импортируем нужные функции из db.py
import os
from config import API_TOKEN, SECRET_PHRASE

bot = telebot.TeleBot(API_TOKEN)

# Множество авторизованных пользователей (chat_id)
authorized_users = set()

# Словарь для хранения ожидания ввода имени исполнителя:
# ключ: chat_id, значение: request_id, для которого менеджер нажал "Взять в работу"
pending_executor = {}

#############################################
# Вспомогательная функция для формирования сообщения заявки

def build_request_message(req):
    """
    Формирует текст заявки и inline-клавиатуру в зависимости от статуса.
    Структура req: (id, fullname, email, phone, subject, message, timestamp, status, executor)
    """
    text = (
        f"📝 <b>Детали заявки:</b>\n\n"
        f"🔹 <b>ID:</b> {req[0]}\n"
        f"🕒 <b>Время:</b> {req[6]}\n"
        f"👤 <b>Имя:</b> {req[1]}\n"
        f"📧 <b>Email:</b> {req[2]}\n"
        f"📞 <b>Телефон:</b> {req[3]}\n"
        f"📝 <b>Тариф:</b> {req[4]}\n"
        f"🚗 <b>Машина и пожелания:</b> {req[5]}\n"
        f"🚨 <b>Статус:</b> {req[7]}\n"
    )
    if req[8]:
        text += f"👨‍💼 <b>Исполнитель:</b> {req[8]}\n"

    markup = types.InlineKeyboardMarkup()
    if req[7] == "new":
        # Если заявка новая, показываем кнопку "Взять в работу"
        markup.add(types.InlineKeyboardButton("✅ Взять в работу", callback_data=f"take:{req[0]}"))
    elif req[7] == "in_progress":
        # Если заявка в работе, показываем кнопки "Успешно" и "Отказ"
        markup.add(types.InlineKeyboardButton("🏁 Успешно", callback_data=f"close:{req[0]}"))
        markup.add(types.InlineKeyboardButton("❌ Отказ", callback_data=f"reject:{req[0]}"))
    elif req[7] in ["completed", "rejected"]:
        # Если заявка закрыта или отклонена, показываем кнопку "Вернуть в работу"
        markup.add(types.InlineKeyboardButton("↩️ Вернуть в работу", callback_data=f"return:{req[0]}"))
    return text, markup

#############################################
# --- Команды бота ---

@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id
    # Ожидаем, что команда будет вида: /start my_secret_phrase
    parts = message.text.strip().split()
    if len(parts) >= 2 and parts[1] == SECRET_PHRASE:
        authorized_users.add(chat_id)
        bot.reply_to(message, "✅ Авторизация успешна. Добро пожаловать в CRM-бот!")
    else:
        bot.reply_to(message, "❌ Неверная секретная фраза. Попробуйте снова.")

@bot.message_handler(commands=['list'])
def handle_list(message):
    if message.chat.id not in authorized_users:
        bot.reply_to(message, "🚫 Вы не авторизованы. Используйте /start <секретная_фраза> для входа.")
        return

    requests = get_all_requests()
    if not requests:
        bot.reply_to(message, "📋 Заявок пока нет.")
        return

    response = "📋 <b>Список заявок:</b>\n"
    for req in requests:
        response += f"\n🔹 <b>ID:</b> {req['id']}\n"
        response += f"🕒 <b>Время:</b> {req['timestamp']}\n"
        response += f"👤 <b>Имя:</b> {req['fullname']}\n"
        response += f"📧 <b>Email:</b> {req['email']}\n"
        response += f"📞 <b>Телефон:</b> {req['phone']}\n"
        response += f"📝 <b>Тариф:</b> {req['subject']}\n"
        response += f"🚗 <b>Машина и пожелания:</b> {req['message']}\n"
        response += f"🚨 <b>Статус:</b> {req['status']}\n"
        if req['executor']:
            response += f"👨‍💼 <b>Исполнитель:</b> {req['executor']}\n"
        response += "-----------------------\n"
    bot.reply_to(message, response, parse_mode='HTML')

# Команда /show <id> — показать заявку с указанным ID
@bot.message_handler(commands=['show'])
def handle_show(message):
    if message.chat.id not in authorized_users:
        bot.reply_to(message, "🚫 Вы не авторизованы. Используйте /start <секретная_фраза> для входа.")
        return

    parts = message.text.strip().split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Укажите ID заявки. Пример: /show 3")
        return

    try:
        request_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат ID. Укажите число.")
        return

    req = get_request_by_id(request_id)
    if not req:
        bot.reply_to(message, f"❌ Заявка с ID {request_id} не найдена.")
        return

    text, markup = build_request_message(req)
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

#############################################
# Обработка inline-кнопок

# Если менеджер нажимает "Взять в работу", бот запрашивает имя исполнителя.
@bot.callback_query_handler(func=lambda call: call.data.startswith("take:"))
def callback_take(call):
    if call.message.chat.id not in authorized_users:
        bot.answer_callback_query(call.id, "🚫 Вы не авторизованы.")
        return

    _, request_id = call.data.split(":")
    pending_executor[call.message.chat.id] = request_id
    bot.send_message(call.message.chat.id, f"Введите имя исполнителя для заявки ID {request_id}:")
    bot.answer_callback_query(call.id)

# Обработчик для ввода имени исполнителя
@bot.message_handler(func=lambda message: message.chat.id in pending_executor)
def handle_executor_input(message):
    chat_id = message.chat.id
    request_id = pending_executor.pop(chat_id, None)
    if request_id:
        executor = message.text.strip()
        update_status(request_id, "in_progress", executor)
        # Получаем обновлённую заявку и обновляем сообщение
        req = get_request_by_id(request_id)
        if req:
            text, markup = build_request_message(req)
            try:
                bot.edit_message_text(text, chat_id, message.message_id, parse_mode='HTML', reply_markup=markup)
            except Exception as e:
                bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=markup)
        bot.reply_to(message, f"✅ Заявка {request_id} принята в работу с исполнителем {executor}.")

# Inline-кнопки для действий: "Успешно" (ранее "Закрыть"), "Отказ" (ранее "Отклонить"), "Вернуть в работу"
@bot.callback_query_handler(func=lambda call: call.data.startswith("close:") or call.data.startswith("reject:") or call.data.startswith("return:"))
def callback_status_change(call):
    if call.message.chat.id not in authorized_users:
        bot.answer_callback_query(call.id, "🚫 Вы не авторизованы.")
        return

    data_parts = call.data.split(":")
    action = data_parts[0]
    request_id = data_parts[1]

    if action == "close":
        update_status(request_id, "completed")
        bot.answer_callback_query(call.id, f"✅ Заявка {request_id} отмечена как успешная.")
    elif action == "reject":
        update_status(request_id, "rejected")
        bot.answer_callback_query(call.id, f"❌ Заявка {request_id} отмечена как отказ.")
    elif action == "return":
        update_status(request_id, "in_progress")
        bot.answer_callback_query(call.id, f"↩️ Заявка {request_id} возвращена в работу.")

    # Получаем обновлённую заявку и обновляем сообщение
    updated_req = get_request_by_id(request_id)
    if updated_req:
        text, markup = build_request_message(updated_req)
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML', reply_markup=markup)
        except Exception as e:
            print("Ошибка обновления сообщения:", e)

#############################################
# Функция для отправки уведомления о новой заявке
def notify_new_request(req):
    text, markup = build_request_message(req)
    for user_id in authorized_users:
        try:
            bot.send_message(user_id, text, parse_mode='HTML', reply_markup=markup)
        except Exception as e:
            print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")

#############################################
# Фоновый поток для опроса базы данных на наличие новых заявок
last_request_id = 0
def poll_new_requests():
    global last_request_id
    while True:
        try:
            requests = get_all_requests()
            if requests:
                max_id = max(req[0] for req in requests)
                if max_id > last_request_id:
                    new_reqs = [req for req in requests if req[0] > last_request_id]
                    for req in new_reqs:
                        notify_new_request(req)
                    last_request_id = max_id
        except Exception as e:
            print("Ошибка опроса новых заявок:", e)
        time.sleep(5)

polling_thread = threading.Thread(target=poll_new_requests, daemon=True)
polling_thread.start()

if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling()
