import asyncio
import json
import random
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode

from config import BOT_TOKEN, ADMIN_ID


bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

print("BOT FILE LOADED")

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

    await bot.send_message(chat_id, q["question"], reply_markup=keyboard)

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
        result_text = (
            f"{q['question']}\n\n"
            f"✔ <b>Верно!</b>\n\n"
            f"Правильный ответ:\n{correct_text}"
        )
    else:
        result_text = (
            f"{q['question']}\n\n"
            f"❌ <b>Неверно</b>\n\n"
            f"Верный ответ:\n{correct_text}"
        )

    await callback.message.edit_text(result_text)
    await asyncio.sleep(2.5)
    await send_question(user_id, callback.message.chat.id)

# ===== ЗАПУСК =====
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("BOT STARTED, polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
