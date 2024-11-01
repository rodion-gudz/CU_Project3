# **Проект 3.** Визуализация для веб-сервиса по предсказанию неблагоприятных погодных условий для путешественников

### API ключ для тестирования

```dotenv
ACCUWEATHER_API_KEY=DvTIGor3G9AjzPN8J2A9BpXgG8knkCRS
```

> Ключ приложен в исходном виде согласно заданию

## Описание проекта

Этот проект – веб-приложение, которое предоставляет прогноз погоды на несколько дней на начальной и конечной точке
маршрута и оценивает наличие неблагоприятных погодных условий

Приложение использует AccuWeather API для получения данных о погоде, а также включает логику для определения и
отображения неблагоприятных условий

## Установка

1. Клонируйте репозиторий:
    ```bash
    git clone https://github.com/rodion-gudz/CU_project3
    cd weather-app
    ```

2. Если у вас не установлен poetry, установите его
    ```bash
    curl -sSL https://install.python-poetry.org | python3 -
    ```

3. Установите зависимости через poetry:
    ```bash
    poetry install
    ```

4. Создайте файл `.env` в корневой директории с вашим API-ключом от AccuWeather:
    ```bash
    ACCUWEATHER_API_KEY=API_TOKEN
    TELEGRAM_BOT_TOKEN=BOT_TOKEN
    INTERNAL_WEATHER_API_URL=http://127.0.0.1:8050/weather
    ```

## Запуск

### Веб

Для запуска приложения выполните следующую команду:

```bash
python -m app
```

Приложение будет доступно по адресу `http://127.0.0.1:8050`

### Бот

Для запуска бота выполните следующую команду:

```bash
python app/bot.py
```

## Функциональность

### Основные функции:

- **Прогноз погоды**: Приложение получает 5-дневный прогноз погоды для указанных городов
- **Оценка неблагоприятных условий**: Для каждого дня прогнозируется наличие следующих неблагоприятных условий:
    - Очень низкая температура (ниже -10°C)
    - Сильный ветер (более 15 м/с)
    - Осадки (дождь или снег)

## Тестирование

### Модульные тесты

В проекте написаны тесты для проверки:

- Правильного определения неблагоприятных условий (низкая температура, сильный ветер, осадки)
- Интеграция с API (мокаем ответы от сервера для тестирования)

Для запуска тестов выполните:

```bash
pytest tests.py
```
