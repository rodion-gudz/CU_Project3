import requests
from flask import Flask, render_template, request

from app.config import get_settings

app = Flask(__name__)

settings = get_settings()

API_KEY = settings.ACCUWEATHER_API_KEY


def is_adverse_condition(day_data):
    max_temp = day_data.get("Temperature", {}).get("Maximum", {}).get("Value", None)
    wind_speed = (
        day_data.get("Day", {}).get("Wind", {}).get("Speed", {}).get("Value", None)
    )
    has_precipitation = day_data.get("Day", {}).get("HasPrecipitation", False)
    precipitation_type = day_data.get("Day", {}).get("PrecipitationType", None)

    if max_temp is None:
        return None

    # температура ниже -10°C
    if max_temp < -10:
        return "Очень низкая температура"

    # ветер сильнее 15 м/с (если данные о ветре присутствуют)
    if wind_speed is not None and wind_speed > 15:
        return "Сильный ветер"

    # осадки: дождь или снег
    if has_precipitation and precipitation_type in ["Rain", "Snow"]:
        return f"Осадки: {precipitation_type}"

    # если нет неблагоприятных условий
    return None


def get_weather(city):
    location_url = f"https://dataservice.accuweather.com/locations/v1/cities/search"
    location_response = requests.get(
        location_url, params={"apikey": API_KEY, "q": city, "language": "ru-ru"}
    )

    if location_response.status_code != 200:
        return {"error": "Не удалось найти город."}

    location_data = location_response.json()
    if isinstance(location_data, list) and len(location_data) == 0:
        return {"error": "Не удалось найти город."}

    location_key = location_data[0]["Key"]

    forecast_url = (
        f"https://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}"
    )
    forecast_response = requests.get(
        forecast_url, params={"apikey": API_KEY, "language": "ru-ru", "metric": True}
    )

    if forecast_response.status_code != 200:
        return {"error": "Не удалось получить прогноз погоды."}

    forecast_data = forecast_response.json()

    forecast = []
    for daily_forecast in forecast_data["DailyForecasts"]:
        adverse_condition = is_adverse_condition(daily_forecast["Day"])
        day_forecast = {
            "day": daily_forecast["Date"],
            "condition": daily_forecast["Day"]["IconPhrase"],
            "temp": f"{daily_forecast['Temperature']['Maximum']['Value']}°C",
            "adverse_condition": adverse_condition,
        }
        forecast.append(day_forecast)

    return {
        "location": city,
        "forecast": forecast,
        "warnings": forecast_data.get("Headline", {}).get("Text", "None"),
    }


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        start_city = request.form.get("start_city")
        end_city = request.form.get("end_city")

        if not start_city or not end_city:
            return render_template(
                "error.html", message="Пожалуйста, введите оба города."
            )

        try:
            start_weather = get_weather(start_city)
            if "error" in start_weather:
                return render_template("error.html", message=start_weather["error"])

            end_weather = get_weather(end_city)
            if "error" in end_weather:
                return render_template("error.html", message=end_weather["error"])

            return render_template(
                "route_weather.html",
                start_weather=start_weather,
                end_weather=end_weather,
            )
        except requests.exceptions.RequestException:
            return render_template(
                "error.html", message="Ошибка сети. Попробуйте позже."
            )

    return render_template("index.html")
