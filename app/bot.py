import logging

import requests
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
from config import get_settings

settings = get_settings()
WEATHER_SERVICE_URL = settings.INTERNAL_WEATHER_API_URL

logging.basicConfig(level=logging.INFO)
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


class WeatherStates(StatesGroup):
    start_city = State()
    intermediate_stops = State()
    end_city = State()
    interval = State()


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.reply(
        "Привет! Я бот, который поможет вам получить прогноз погоды для маршрута. "
        "Введите команду /weather, чтобы начать."
    )


@dp.message_handler(commands=["help"])
async def help(message: types.Message):
    await message.reply(
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/weather - Получить прогноз погоды для маршрута"
    )


@dp.message_handler(commands=["weather"])
async def weather(message: types.Message):
    await message.reply(
        "Введите начальный город маршрута или отправьте своё местоположение:"
    )
    await WeatherStates.start_city.set()


# команда /done для завершения добавления промежуточных точек
@dp.message_handler(commands=["done"], state=WeatherStates.intermediate_stops)
async def finish_intermediate_stops(message: types.Message, state: FSMContext):
    await message.reply(
        "Введите конечный город маршрута или отправьте своё местоположение."
    )
    await WeatherStates.end_city.set()


# обработка начального города
@dp.message_handler(
    state=WeatherStates.start_city,
    content_types=[types.ContentType.TEXT, types.ContentType.LOCATION],
)
async def process_start_city(message: types.Message, state: FSMContext):
    if message.content_type == types.ContentType.LOCATION:
        latitude = message.location.latitude
        longitude = message.location.longitude
        await state.update_data(start_city=f"{latitude},{longitude}")
    else:
        await state.update_data(start_city=message.text)
    await message.reply(
        "Добавьте промежуточные точки маршрута или введите конечный город (отправьте /done, если готовы продолжить):"
    )
    await WeatherStates.intermediate_stops.set()


# обработка промежуточных точек маршрута
@dp.message_handler(
    state=WeatherStates.intermediate_stops,
    content_types=[types.ContentType.TEXT, types.ContentType.LOCATION],
)
async def process_intermediate_stop(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if "stops" not in data:
            data["stops"] = []
        if message.content_type == types.ContentType.LOCATION:
            latitude = message.location.latitude
            longitude = message.location.longitude
            data["stops"].append(f"{latitude},{longitude}")
        else:
            data["stops"].append(message.text)
    await message.reply(
        "Промежуточная точка добавлена. Введите следующую точку или отправьте /done, если готовы продолжить."
    )


# обработка конечного города
@dp.message_handler(
    state=WeatherStates.end_city,
    content_types=[types.ContentType.TEXT, types.ContentType.LOCATION],
)
async def process_end_city(message: types.Message, state: FSMContext):
    if message.content_type == types.ContentType.LOCATION:
        latitude = message.location.latitude
        longitude = message.location.longitude
        await state.update_data(end_city=f"{latitude},{longitude}")
    else:
        await state.update_data(end_city=message.text)

    interval_keyboard = InlineKeyboardMarkup(row_width=2)
    interval_keyboard.add(
        InlineKeyboardButton("Прогноз на 3 дня", callback_data="interval_3"),
        InlineKeyboardButton("Прогноз на 5 дней", callback_data="interval_5"),
        InlineKeyboardButton("Прогноз на неделю", callback_data="interval_7"),
    )

    await message.reply(
        "Выберите временной интервал прогноза:", reply_markup=interval_keyboard
    )
    await WeatherStates.interval.set()


# обработка выбора интервала прогноза
@dp.callback_query_handler(
    lambda c: c.data and c.data.startswith("interval"), state=WeatherStates.interval
)
async def process_interval(callback_query: types.CallbackQuery, state: FSMContext):
    interval = int(callback_query.data.split("_")[1])
    await state.update_data(interval=interval)

    # Получение данных из состояния
    user_data = await state.get_data()
    start_city = user_data["start_city"]
    end_city = user_data["end_city"]
    intermediate_stops = user_data.get("stops", [])

    await callback_query.message.answer(
        f"Получаю прогноз погоды для маршрута: {start_city} - {' - '.join(intermediate_stops)} - {end_city} на {interval} дней..."
    )

    try:
        response = requests.get(
            WEATHER_SERVICE_URL,
            params={
                "start_city": start_city,
                "end_city": end_city,
                "stops": intermediate_stops,
                "interval": interval,
            },
        )
        response.raise_for_status()
        weather_data = response.json()

        # Форматирование ответа для каждого города на маршруте
        weather_text = f"Прогноз погоды для маршрута:\n\n"
        for city_data in weather_data.get("route", []):
            city = city_data["city"]
            weather_text += f"{city}:\n"
            for day in city_data["forecast"]:
                weather_text += (
                    f"{day['day']}: {day['condition']}\n"
                    f"Макс. температура: {day['temp_max']}°C\n"
                    f"Мин. температура: {day['temp_min']}°C\n"
                    f"Интенсивность осадков: {day['precip_intensity']}\n\n"
                )
            weather_text += "\n"  # Разделение между городами
        await callback_query.message.answer(weather_text)

    except requests.exceptions.RequestException:
        await callback_query.message.answer(
            "Не удалось получить данные прогноза. Попробуйте позже."
        )

    await state.finish()


# обработка ошибок
@dp.errors_handler()
async def error_handler(update, exception):
    logging.exception(f"Произошла ошибка: {exception}")
    if isinstance(update, types.Update):
        await update.message.reply("Произошла ошибка. Попробуйте снова.")
    return True


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
