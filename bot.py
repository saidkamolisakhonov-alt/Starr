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
        "correct": None,
        "options": None
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

    # индекс правильного ответа в перемешанном списке
    correct = next(i for i, o in enumerate(indexed) if o[0] == q["correct"])

    user_sessions[user_id]["correct"] = correct
    user_sessions[user_id]["options"] = options

    letters = ["A", "B", "C", "D", "E", "F"]

    # ===== текст вопроса + варианты =====
    text = f"📝 {q['question']}\n\n"
    for i, opt in enumerate(options):
        text += f"{letters[i]}) {opt}\n\n"

    # ===== кнопки 2×2 =====
    rows = []
    row = []

    for i in range(len(options)):
        row.append(InlineKeyboardButton(text=letters[i], callback_data=str(i)))
        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await bot.send_message(chat_id, text, reply_markup=kb)

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

    # правильный вариант (в перемешанном виде)
    options = session.get("options", q["options"])
    correct_text = options[correct_answer]

    if user_answer == correct_answer:
        result = "✅ Верно! ✅"
    else:
        result = "❌ Неверно"

    text = (
    f"{result}\n\n"
    f"📝 {q['question']}\n\n"
    f"Правильный ответ:\n"
    f"<b>{correct_text}</b>"
    )


    await callback.message.edit_text(text, reply_markup=None, parse_mode="HTML")
    await callback.answer()

    await asyncio.sleep(1.5)
    await send_question(user_id, callback.message.chat.id)

# ================== ADMIN ==================
@dp.message(Command("usinfo"))
async def usinfo(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    users_list = load_json("users.json", [])

    text = f"👥 Пользователей: {len(users_list)}\n\n"
    for u in users_list:
        text += (
            f"{u.get('first_name', 'Без имени')} (@{u.get('username')})\n"
            f"ID: {u['id']}\n"
            f"С: {u['joined']}\n\n"
        )

    await message.answer(text)

@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("❗ Напиши текст после /broadcast")
        return

    users_list = load_json("users.json", [])

    sent = 0
    failed = 0

    for u in users_list:
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

# ================== START ==================
async def main():
    print("🤖 Bot started (Railway)")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
