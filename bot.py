import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


# ================== CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [5640388317]

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

registered_users = {}


# ================== KEYBOARDS ==================
faculty_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Raqamli iqtisodiyot va axborot texnologiyalari")],
        [KeyboardButton(text="Iqtisodiyot")],
        [KeyboardButton(text="Menejment")],
        [KeyboardButton(text="Turizm")],
        [KeyboardButton(text="Bank ishi")],
        [KeyboardButton(text="TDIU-PDU qo'shma ta'lim fakulteti")],
        [KeyboardButton(text="Pendidikan xalqaro qoʻshma taʼlim fakulteti")],
        [KeyboardButton(text="TDIU-URDIU qo'shma ta'lim dasturi fakulteti")],
        [KeyboardButton(text="TDIU To'rtko'l fakulteti")],
        [KeyboardButton(text="Soliq va budjet hisobi fakulteti")],
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


# ================== START ==================
@dp.message(CommandStart())
async def welcome(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in registered_users:
        await message.answer(
            "Assalomu alaykum!\nIltimos, fakultetingizni tanlang 👇",
            reply_markup=faculty_keyboard
        )
        await state.set_state(RegistrationState.faculty)
    else:
        await message.answer("Asosiy menyu 👇", reply_markup=menu)


@dp.message(RegistrationState.faculty)
async def register_faculty(message: types.Message, state: FSMContext):
    await state.update_data(faculty=message.text)
    await message.answer("Guruhingizni yozing:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(RegistrationState.group)


@dp.message(RegistrationState.group)
async def register_group(message: types.Message, state: FSMContext):
    await state.update_data(group=message.text)
    contact_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamini yuborish", request_contact=True)]],
        resize_keyboard=True
    )
    await message.answer("Telefon raqamingizni yuboring:", reply_markup=contact_kb)
    await state.set_state(RegistrationState.phone)


@dp.message(RegistrationState.phone, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()

    registered_users[user_id] = {
        "faculty": data["faculty"],
        "group": data["group"],
        "phone": message.contact.phone_number
    }

    await state.clear()
    await message.answer("✅ Ro‘yxatdan muvaffaqiyatli o‘tdingiz!", reply_markup=menu)


# ================== MUROJAAT ==================
@dp.message(F.text == "📩 Murojaat yuborish")
async def ask_for_request(message: types.Message):
    if message.from_user.id in registered_users:
        await message.answer("✍️ Murojaatingizni yozing.")
    else:
        await message.answer("❗ Avval ro‘yxatdan o‘ting. /start")


@dp.message()
async def send_request(message: types.Message):
    user_id = message.from_user.id
    if user_id not in registered_users:
        return

    user = registered_users[user_id]

    text = (
        f"📩 Yangi murojaat\n\n"
        f"👤 Talaba: {message.from_user.full_name}\n"
        f"🏫 Fakultet: {user['faculty']}\n"
        f"🎓 Guruh: {user['group']}\n"
        f"📞 Tel: {user['phone']}\n\n"
        f"✉️ Murojaat:\n{message.text}"
    )

    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, text)

    await message.answer("✅ Murojaatingiz yuborildi!")


# ================== MAIN ==================
async def main():
    logging.info("Bot ishga tushdi")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
