import asyncio
import json
import random
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# ================== ENV ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN is not set in Railway Variables")

# ================== BOT ==================
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ================== DATA ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_json(name, default):
    path = os.path.join(BASE_DIR, name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(name, data):
    path = os.path.join(BASE_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

QUESTIONS = load_json("questions.json", [])
users = load_json("users.json", [])

user_sessions = {}

# ================== USERS ==================
def save_user(user: types.User):
    if any(u["id"] == user.id for u in users):
        return

    users.append({
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "joined": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_json("users.json", users)

# ================== GAME ==================
def init_session(user_id: int):
    order = list(range(len(QUESTIONS)))
    random.shuffle(order)
    user_sessions[user_id] = {
        "order": order,
        "current": None,
        "correct": None
    }

def get_question(user_id: int):
    session = user_sessions[user_id]
    if not session["order"]:
        session["order"] = list(range(len(QUESTIONS)))
        random.shuffle(session["order"])

    q_index = session["order"].pop()
    session["current"] = q_index
    return QUESTIONS[q_index]

async def send_question(user_id: int, chat_id: int):
    q = get_question(user_id)

    indexed = list(enumerate(q["options"]))
    random.shuffle(indexed)

    options = [o[1] for o in indexed]
    correct = next(i for i, o in enumerate(indexed) if o[0] == q["correct"])
    user_sessions[user_id]["correct"] = correct

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=str(i))]
            for i, opt in enumerate(options)
        ]
    )

    await bot.send_message(chat_id, q["question"], reply_markup=kb)

# ================== HANDLERS ==================
@dp.message(CommandStart())
async def start(message: types.Message):
    save_user(message.from_user)
    init_session(message.from_user.id)
    await send_question(message.from_user.id, message.chat.id)

@dp.callback_query()
async def answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    session = user_sessions.get(user_id)

    if not session:
        await callback.answer()
        return

    user_answer = int(callback.data)
    correct_answer = session["correct"]

    q = QUESTIONS[session["current"]]
    correct_text = q["options"][q["correct"]]

    if user_answer == correct_answer:
        text = f"{q['question']}\n\n✅ Верно!\n\nОтвет:\n{correct_text}"
    else:
        text = f"{q['question']}\n\n❌ Неверно\n\nВерный ответ:\n{correct_text}"

    await callback.message.edit_text(text)
    await asyncio.sleep(2)
    await send_question(user_id, callback.message.chat.id)

# ================== ADMIN ==================
@dp.message(Command("usinfo"))
async def usinfo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = f"👥 Пользователей: {len(users)}\n\n"
    for u in users[-10:]:
        text += f"{u['first_name']} (@{u['username']})\nID: {u['id']}\n\n"

    await message.answer(text)

# ================== START ==================
async def main():
    print("🤖 Bot started (Railway)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
