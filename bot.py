import asyncio
import logging
import os
import sqlite3
import threading  # Yangi qo'shildi
from flask import Flask  # Yangi qo'shildi

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================== WEB SERVER (Render uchun) ==================
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running!", 200

def run_flask():
    # Render avtomatik beradigan PORT ni olamiz, bo'lmasa 10000
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# ================== CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [6601319172, 8256749887]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ================== DATABASE ==================
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    full_name TEXT,
    faculty TEXT,
    group_name TEXT,
    phone TEXT
)
""")
conn.commit()

def is_registered(user_id: int) -> bool:
    cursor.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None

def save_user(user_id, full_name, faculty, group, phone):
    cursor.execute("""
    INSERT OR REPLACE INTO users
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, full_name, faculty, group, phone))
    conn.commit()

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

# ================== KEYBOARDS ==================
faculty_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Raqamli iqtisodiyot va axborot texnologiyalari")],
        [KeyboardButton(text="Iqtisodiyot")],
        [KeyboardButton(text="Menejment")],
        [KeyboardButton(text="Turizm")],
        [KeyboardButton(text="Bank ishi")],
    ],
    resize_keyboard=True
)

menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📩 Murojaat yuborish")]],
    resize_keyboard=True
)

# ================== FSM ==================
class RegistrationState(StatesGroup):
    faculty = State()
    group = State()
    phone = State()

# ================== HANDLERS ==================
@dp.message(CommandStart())
async def start(message: types.Message, state: FSMContext):
    if not is_registered(message.from_user.id):
        await message.answer(
            "Assalomu alaykum!\nFakultetingizni tanlang 👇",
            reply_markup=faculty_keyboard
        )
        await state.set_state(RegistrationState.faculty)
    else:
        await message.answer("Asosiy menyu 👇", reply_markup=menu)

@dp.message(RegistrationState.faculty)
async def reg_faculty(message: types.Message, state: FSMContext):
    await state.update_data(faculty=message.text)
    await message.answer("Guruhingizni yozing:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(RegistrationState.group)

@dp.message(RegistrationState.group)
async def reg_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamini yuborish", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer("Telefon raqamingizni yuboring:", reply_markup=kb)
    await state.set_state(RegistrationState.phone)

@dp.message(RegistrationState.phone, F.contact)
async def reg_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    save_user(
        message.from_user.id,
        message.from_user.full_name,
        data["faculty"],
        data["group"],
        message.contact.phone_number
    )
    await state.clear()
    await message.answer("✅ Ro‘yxatdan o‘tdingiz!", reply_markup=menu)

@dp.message(F.text == "📩 Murojaat yuborish")
async def ask_request(message: types.Message):
    if is_registered(message.from_user.id):
        await message.answer("✍️ Murojaatingizni yozing.")
    else:
        await message.answer("❗ Avval ro‘yxatdan o‘ting. /start")

@dp.message()
async def handle_request(message: types.Message):
    if not is_registered(message.from_user.id):
        return

    user = get_user(message.from_user.id)
    if not user: return
    
    _, full_name, faculty, group, phone = user

    text = (
        f"📩 Yangi murojaat\n\n"
        f"👤 Talaba: {full_name}\n"
        f"🏫 Fakultet: {faculty}\n"
        f"🎓 Guruh: {group}\n"
        f"📞 Tel: {phone}\n\n"
        f"✉️ Murojaat:\n{message.text}"
    )

    for admin in ADMIN_IDS:
        try:
            await bot.send_message(admin, text)
        except Exception as e:
            logging.error(f"Admin {admin}ga xabar ketmadi: {e}")

    await message.answer("✅ Murojaatingiz yuborildi!")

# ================== MAIN ==================
async def main():
    # Flaskni alohida "thread"da ishga tushiramiz
    threading.Thread(target=run_flask, daemon=True).start()
    
    logging.info("Bot ishga tushdi")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
