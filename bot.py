import asyncio
import json
import random
from datetime import datetime

import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Получаем токены из переменных окружения (Secrets)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables!")

bot = Bot(TOKEN)
dp = Dispatcher()

# ===== ЗАГРУЗКА ВОПРОСОВ =====
with open("questions.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)

# ===== СЕССИИ ПОЛЬЗОВАТЕЛЕЙ =====
user_sessions = {}

# ===== СОХРАНЕНИЕ ПОЛЬЗОВАТЕЛЕЙ =====
def save_user(user):
    try:
        with open("users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    if not any(u["id"] == user.id for u in users):
        users.append({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "joined": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

# ===== ИНИЦИАЛИЗАЦИЯ СЕССИИ =====
def init_session(user_id: int):
    order = list(range(len(QUESTIONS)))
    random.shuffle(order)
    user_sessions[user_id] = {
        "order": order,
        "current_q": None,
        "correct_index": None
    }

def get_next_question(user_id: int):
    session = user_sessions[user_id]

    if not session["order"]:
        session["order"] = list(range(len(QUESTIONS)))
        random.shuffle(session["order"])

    q_index = session["order"].pop()
    session["current_q"] = q_index
    return QUESTIONS[q_index]

# ===== ОТПРАВКА ВОПРОСА =====
async def send_question(user_id: int, chat_id: int):
    q = get_next_question(user_id)

    indexed = list(enumerate(q["options"]))
    random.shuffle(indexed)

    options = [o[1] for o in indexed]
    correct_index = next(
        i for i, o in enumerate(indexed)
        if o[0] == q["correct"]
    )

    user_sessions[user_id]["correct_index"] = correct_index

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=str(i))]
            for i, opt in enumerate(options)
        ]
    )

    await bot.send_message(
        chat_id,
        q["question"],
        reply_markup=keyboard
    )

# ===== /START =====
@dp.message(CommandStart())
async def start(message: types.Message):
    save_user(message.from_user)
    init_session(message.from_user.id)
    await send_question(message.from_user.id, message.chat.id)

# ===== ОБРАБОТКА ОТВЕТА =====
@dp.callback_query()
async def handle_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    session = user_sessions.get(user_id)

    if not session:
        await callback.answer()
        return

    user_answer = int(callback.data)
    correct_answer = session["correct_index"]

    q = QUESTIONS[session["current_q"]]
    correct_text = q["options"][q["correct"]]

    if user_answer == correct_answer:
        result_text = f"{q['question']}\n\n✔ **Верно!**\n\nПравильный ответ:\n{correct_text}"
    else:
        result_text = f"{q['question']}\n\n❌ **Неверно**\n\nВерный ответ:\n{correct_text}"

    # Редактируем сообщение с вопросом, заменяя его на результат
    await callback.message.edit_text(text=result_text, reply_markup=None, parse_mode="Markdown")

    await asyncio.sleep(2.5)
    await send_question(user_id, callback.message.chat.id)

# ===== /USINFO (ТОЛЬКО АДМИН) =====
@dp.message(Command("usinfo"))
async def usinfo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    try:
        with open("users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    text = f"👥 Пользователи бота\n\nВсего: {len(users)}\n\n"

    for u in users[-10:]:
        text += (
            f"• {u['first_name'] or 'Без имени'} "
            f"(@{u['username']})\n"
            f"ID: {u['id']}\n"
            f"С: {u['joined']}\n\n"
        )

    await message.answer(text)

# ===== /BROADCAST (ТОЛЬКО АДМИН) =====
@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.replace("/broadcast", "").strip()
    if not text:
        await message.answer("❗ Напиши текст после /broadcast")
        return

    try:
        with open("users.json", "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        users = []

    sent = 0
    failed = 0

    for u in users:
        try:
            await bot.send_message(
                u["id"],
                f"📢 Сообщение от администратора:\n\n{text}"
            )
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1

    await message.answer(
        f"✅ Рассылка завершена\n\n"
        f"Отправлено: {sent}\n"
        f"Не доставлено: {failed}"
    )

# ===== ЗАПУСК =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
