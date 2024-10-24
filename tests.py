import pytest
from app.web import app, is_adverse_condition


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


# Тест 1: Проверка главной страницы
def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Прогноз погоды на маршруте" in response.text


# Тест 2: Проверка обработки пустого ввода начальной и конечной точки
def test_empty_city_input(client):
    response = client.post("/", data={"start_city": "", "end_city": ""})
    assert response.status_code == 200
    assert "Пожалуйста, введите оба города." in response.text


# Тест 3: Проверка корректного ввода городов (используем мок-данные для подмены реального API)
def test_valid_route(client, mocker, capsys):
    mock_start_weather_data = {
        "location": "Москва",
        "forecast": [
            {"day": "Понедельник", "condition": "Солнечно", "temp": "25°C"},
            {"day": "Вторник", "condition": "Дождь", "temp": "20°C"},
        ],
        "warnings": "None",
    }

    mock_end_weather_data = {
        "location": "Санкт-Петербург",
        "forecast": [
            {"day": "Понедельник", "condition": "Облачно", "temp": "15°C"},
            {"day": "Вторник", "condition": "Снег", "temp": "0°C"},
        ],
        "warnings": "None",
    }

    # Мокаем вызов для обоих городов
    mocker.patch("app.web.get_weather", side_effect=[mock_start_weather_data, mock_end_weather_data])

    response = client.post("/", data={"start_city": "Москва", "end_city": "Санкт-Петербург"})
    assert response.status_code == 200
    assert "Начальный город: Москва" in response.text
    assert "Конечный город: Санкт-Петербург" in response.text
    assert "Понедельник" in response.text
    assert "Солнечно" in response.text
    assert "Облачно" in response.text


# Тест 4: Проверка некорректного города
def test_invalid_city(client, mocker):
    mocker.patch(
        "app.web.get_weather", return_value={"error": "Не удалось найти город."}
    )

    response = client.post("/", data={"start_city": "НекорректныйГород", "end_city": "НекорректныйГород2"})
    assert response.status_code == 200
    assert "Не удалось найти город." in response.text


# Тест 5: Проверка неблагоприятных погодных условий
def test_adverse_conditions():
    # низкая температура
    cold_day = {
        "Temperature": {"Maximum": {"Value": -15}},
        "Day": {"Wind": {"Speed": {"Value": 5}}, "HasPrecipitation": False},
    }
    assert (
        is_adverse_condition(cold_day) == "Очень низкая температура"
    ), "Ошибка: Низкая температура не распознана"

    # сильный ветер
    windy_day = {
        "Temperature": {"Maximum": {"Value": 10}},
        "Day": {"Wind": {"Speed": {"Value": 20}}, "HasPrecipitation": False},
    }
    assert (
        is_adverse_condition(windy_day) == "Сильный ветер"
    ), "Ошибка: Сильный ветер не распознан"

    # осадки (дождь)
    rainy_day = {
        "Temperature": {"Maximum": {"Value": 12}},
        "Day": {
            "Wind": {"Speed": {"Value": 10}},
            "HasPrecipitation": True,
            "PrecipitationType": "Rain",
        },
    }
    assert (
        is_adverse_condition(rainy_day) == "Осадки: Rain"
    ), "Ошибка: Дождь не распознан как неблагоприятное условие"

    # благоприятные условия
    good_day = {
        "Temperature": {"Maximum": {"Value": 25}},
        "Day": {"Wind": {"Speed": {"Value": 5}}, "HasPrecipitation": False},
    }
    assert (
        is_adverse_condition(good_day) is None
    ), "Ошибка: Благоприятные условия были определены как неблагоприятные"

    # осадки (снег)
    snowy_day = {
        "Temperature": {"Maximum": {"Value": -5}},
        "Day": {
            "Wind": {"Speed": {"Value": 10}},
            "HasPrecipitation": True,
            "PrecipitationType": "Snow",
        },
    }
    assert (
        is_adverse_condition(snowy_day) == "Осадки: Snow"
    ), "Ошибка: Снег не распознан как неблагоприятное условие"
