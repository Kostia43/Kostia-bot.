import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

# Твой токен
API_TOKEN = '7128709825:AAHOMWhmaMttX1CHUaoWh8hmDQb66ouCqi8'

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Чат для отправки чеков
CHECKS_CHAT_ID = '@LavkaProjectsChecks'

# Реквизиты для оплаты
PAYMENT_DETAILS = "Переведи указанную сумму на карту 2202 2061 9318 1224 (Сбер) и пришли чек."

# Файл для хранения заблокированных пользователей
BLOCKED_USERS_FILE = "blocked_users"

# Список файлов с ценами
FILES = {
    "Операция Д - 75₽": ("files/Десантная операция [Conspiracy].gbsave", "Операция Д", 75),
    "Спадси - 178₽": ("files/Ресторан быстрого питания [Plains].gbsave", "Спадси", 178),
    "Бакшот Рулет - 22₽": ("files/Buckshot roulette [Legacy].gbsave", "Бакшот Рулет", 22),
    "Концерт - 32₽": ("files/Концерт [Afterglow].gbsave", "Концерт", 32),
    "Злой Дух - 9₽": ("files/Злой дух [Facility].gbsave", "Злой Дух", 9),
}

# Словарь для отслеживания покупок пользователей
pending_payments = {}


# Функция для загрузки списка заблокированных пользователей
def load_blocked_users():
    try:
        with open(BLOCKED_USERS_FILE, "r") as file:
            return set(map(int, file.read().splitlines()))
    except FileNotFoundError:
        return set()


# Функция для сохранения списка заблокированных пользователей
def save_blocked_users(blocked_users):
    with open(BLOCKED_USERS_FILE, "w") as file:
        file.write("\n".join(map(str, blocked_users)))


# Функция для блокировки пользователя
def block_user(user_id):
    blocked_users = load_blocked_users()
    blocked_users.add(user_id)
    save_blocked_users(blocked_users)


# Функция для разблокировки пользователя
def unblock_user(user_id):
    blocked_users = load_blocked_users()
    blocked_users.discard(user_id)
    save_blocked_users(blocked_users)


# Фильтр для проверки, заблокирован ли пользователь
async def is_blocked(message: types.Message):
    blocked_users = load_blocked_users()
    return message.from_user.id in blocked_users


# Команда старт
@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    if await is_blocked(message):
        await message.reply("Вы заблокированы и не можете использовать бота.")
        return
    await message.reply("Приветствую, путник! Что желаешь? Напиши /buy, чтобы посмотреть каталог товаров.")


# Команда для просмотра каталога
@dp.message(Command('buy'))
async def send_catalog(message: types.Message):
    if await is_blocked(message):
        await message.reply("Вы заблокированы и не можете использовать бота.")
        return
    await message.reply("Выбери проект для покупки:", reply_markup=types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=name)] for name in FILES.keys()],
        resize_keyboard=True,
        one_time_keyboard=True
    ))


# Обработка выбора файлов (отправка реквизитов для оплаты)
@dp.message(lambda message: message.text in FILES)
async def request_payment(message: types.Message):
    if await is_blocked(message):
        await message.reply("Вы заблокированы и не можете использовать бота.")
        return
    file_info = FILES[message.text]
    pending_payments[message.from_user.id] = file_info  # Запоминаем выбор пользователя
    await message.reply(
        f"{PAYMENT_DETAILS}\n\nСумма к оплате: {file_info[2]}₽\nПосле оплаты отправь скриншот чека сюда."
    )
    await message.reply("ВНИМАНИЕ! При выходе Обновлений для этого Проекта, Обновление придётся покупать Заново По полной Стоимости!")


# Обработка отправки чека (фото) и пересылка в чат для проверки
@dp.message(lambda message: message.photo)
async def handle_payment_proof(message: types.Message):
    if await is_blocked(message):
        await message.reply("Вы заблокированы и не можете использовать бота.")
        return 

    user_id = message.from_user.id
    if user_id in pending_payments:
        file_info = pending_payments[user_id]  # Получаем информацию о покупке

        # Отправляем чек и ID покупателя в чат для проверки
        caption = f"Чек на оплату {file_info[1]} ({file_info[2]}₽)\nID покупателя: {user_id}"
        await bot.send_photo(CHECKS_CHAT_ID, message.photo[-1].file_id, caption=caption, parse_mode="Markdown")

        # Подтверждение пользователю
        await message.reply("Чек отправлен на проверку! Ожидайте подтверждения и получения файла.")
    else:
        await message.reply("Не найдено ожидающих платежей. Убедись, что ты выбрал товар перед оплатой.")


# Команда для отправки файла после проверки
@dp.message(lambda message: message.text.startswith("/sendfile"))
async def send_purchased_file(message: types.Message):
    if await is_blocked(message):
        await message.reply("Вы заблокированы и не можете использовать бота.")
        return

    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Используй команду в формате: /sendfile <user_id>")
        return
    
    user_id = int(parts[1])
    if user_id in pending_payments:
        file_info = pending_payments.pop(user_id)
        file_path, file_name, price = file_info
        file = FSInputFile(file_path)

        await bot.send_document(user_id, file, caption=f"Спасибо за покупку! Вот ваш файл: {file_name}.")
        await message.reply(f"Файл {file_name} отправлен пользователю {user_id}.")
    else:
        await message.reply("Не найдено ожидающих платежей для этого пользователя.")


# Команда для блокировки пользователя
@dp.message(lambda message: message.text.startswith("/block"))
async def block_command(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Используй команду в формате: /block <user_id>")
        return

    user_id = int(parts[1])
    block_user(user_id)
    await message.reply(f"Пользователь {user_id} заблокирован.")


# Команда для разблокировки пользователя
@dp.message(lambda message: message.text.startswith("/unblock"))
async def unblock_command(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.reply("Используй команду в формате: /unblock <user_id>")
        return

    user_id = int(parts[1])
    unblock_user(user_id)
    await message.reply(f"Пользователь {user_id} разблокирован.")


# Запуск бота
if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))