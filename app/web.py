import dash
import dash_bootstrap_components as dbc
import folium
import plotly.graph_objs as go
import requests
from dash import Input, Output, State, dcc, html
from flask import Flask, jsonify, request
from folium.plugins import MarkerCluster

from app.config import get_settings

settings = get_settings()
API_KEY = settings.ACCUWEATHER_API_KEY

server = Flask(__name__)
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])


def get_weather(city, days=5):
    location_url = f"https://dataservice.accuweather.com/locations/v1/cities/search"
    location_response = requests.get(
        location_url, params={"apikey": API_KEY, "q": city, "language": "ru-ru"}
    )
    if location_response.status_code != 200:
        return {"error": "Не удалось найти город."}

    location_data = location_response.json()
    if not location_data:
        return {"error": "Не удалось найти город."}

    location_key = location_data[0]["Key"]
    forecast_url = f"https://dataservice.accuweather.com/forecasts/v1/daily/{days}day/{location_key}"
    forecast_response = requests.get(
        forecast_url, params={"apikey": API_KEY, "language": "ru-ru", "metric": True}
    )
    if forecast_response.status_code != 200:
        return {"error": "Не удалось получить прогноз погоды."}

    forecast_data = forecast_response.json()
    forecast = [
        {
            "day": daily_forecast["Date"],
            "condition": daily_forecast["Day"]["IconPhrase"],
            "temp_max": daily_forecast["Temperature"]["Maximum"]["Value"],
            "temp_min": daily_forecast["Temperature"]["Minimum"]["Value"],
            "precip_intensity": daily_forecast["Day"].get(
                "PrecipitationIntensity", "None"
            ),
        }
        for daily_forecast in forecast_data["DailyForecasts"]
    ]
    return {
        "location": city,
        "latitude": location_data[0].get("GeoPosition", {}).get("Latitude", 0),
        "longitude": location_data[0].get("GeoPosition", {}).get("Longitude", 0),
        "forecast": forecast,
        "warnings": forecast_data.get("Headline", {}).get("Text", "None"),
    }


# эндпоинт для получения прогноза по запросу бота
@server.route("/weather", methods=["GET"])
def api_get_weather():
    start_city = request.args.get("start_city")
    end_city = request.args.get("end_city")
    interval = int(request.args.get("interval", 5))
    stops = request.args.getlist("stops")

    if not start_city or not end_city:
        return jsonify({"error": "Начальный и конечный города обязательны"}), 400

    route_forecast = []

    start_weather = get_weather(start_city, days=interval)
    if "error" in start_weather:
        return jsonify({"error": start_weather["error"]}), 400
    route_forecast.append({"city": start_city, "forecast": start_weather["forecast"]})

    for stop in stops:
        stop_weather = get_weather(stop, days=interval)
        if "error" in stop_weather:
            return jsonify({"error": stop_weather["error"]}), 400
        route_forecast.append({"city": stop, "forecast": stop_weather["forecast"]})

    end_weather = get_weather(end_city, days=interval)
    if "error" in end_weather:
        return jsonify({"error": end_weather["error"]}), 400
    route_forecast.append({"city": end_city, "forecast": end_weather["forecast"]})

    response_data = {"route": route_forecast, "interval": interval}
    return jsonify(response_data)


# форма с возможностью добавления промежуточных точек
app.layout = dbc.Container(
    [
        html.H1("Прогноз погоды для маршрута", className="my-4"),
        html.Label("Выберите интервал прогноза"),
        dcc.RadioItems(
            id="interval-selector",
            options=[
                {"label": "3 дня", "value": 3},
                {"label": "5 дней", "value": 5},
                {"label": "7 дней", "value": 7},
            ],
            value=5,
            inline=True,
            className="mb-3",
        ),
        html.Label("Выберите параметр для графика"),
        dcc.Dropdown(
            id="parameter-dropdown",
            options=[
                {"label": "Максимальная температура", "value": "temp_max"},
                {"label": "Минимальная температура", "value": "temp_min"},
                {"label": "Интенсивность осадков", "value": "precip_intensity"},
            ],
            value="temp_max",
            clearable=False,
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Input(
                        id="start-city",
                        placeholder="Введите начальный город",
                        type="text",
                    ),
                    width=4,
                ),
                dbc.Col(
                    dbc.Input(
                        id="end-city", placeholder="Введите конечный город", type="text"
                    ),
                    width=4,
                ),
            ],
            className="mb-2",
        ),
        dbc.Button(
            "Добавить промежуточную точку",
            id="add-stop-btn",
            color="secondary",
            className="mb-3",
        ),
        html.Div(id="stops-container"),
        dbc.Button(
            "Получить прогноз", id="submit-button", color="primary", className="mb-4"
        ),
        dcc.Graph(id="weather-graph"),
        html.Div(id="output-weather"),
        html.Iframe(id="map", width="100%", height="500"),
    ]
)


# callback для динамического добавления полей промежуточных точек
@app.callback(
    Output("stops-container", "children"),
    Input("add-stop-btn", "n_clicks"),
    State("stops-container", "children"),
)
def add_stop(n_clicks, children):
    if n_clicks is None:
        return children
    if children is None:
        children = []
    new_stop = dbc.Input(
        id={"type": "stop-city", "index": n_clicks},
        placeholder=f"Промежуточная точка {n_clicks}",
        type="text",
        className="mb-2",
    )
    children.append(new_stop)
    return children


# callback для обработки прогноза и обновления графиков и карты
@app.callback(
    [
        Output("output-weather", "children"),
        Output("weather-graph", "figure"),
        Output("map", "srcDoc"),
    ],
    [
        Input("submit-button", "n_clicks"),
        Input("interval-selector", "value"),
        Input("parameter-dropdown", "value"),
    ],
    [
        State("start-city", "value"),
        State("end-city", "value"),
        State("stops-container", "children"),
    ],
)
def update_weather(n_clicks, interval, parameter, start_city, end_city, stops):
    if not n_clicks:
        return "", go.Figure(), ""

    if not start_city or not end_city:
        return (
            dbc.Alert(
                "Пожалуйста, введите начальный и конечный города.", color="danger"
            ),
            go.Figure(),
            "",
        )

    if stops is None:
        stops = []

    cities = (
        [start_city]
        + [stop["props"]["value"] for stop in stops if stop["props"]["value"]]
        + [end_city]
    )

    weather_data = []
    for city in cities:
        city_weather = get_weather(city, days=interval)
        if "error" in city_weather:
            return dbc.Alert(city_weather["error"], color="danger"), go.Figure(), ""
        weather_data.append(city_weather)

    # построение графика на основе выбранного параметра
    fig = go.Figure()
    for city_weather in weather_data:
        fig.add_trace(
            go.Scatter(
                x=[day["day"] for day in city_weather["forecast"]],
                y=[day[parameter] for day in city_weather["forecast"]],
                mode="lines+markers",
                name=f"{city_weather['location']} - {parameter}",
            )
        )
    fig.update_layout(
        title=f"Прогноз погоды ({parameter}) на {interval} дней",
        xaxis_title="День",
        yaxis_title="Значение",
    )

    # создание карты маршрута
    start_lat = weather_data[0]["latitude"]
    start_lon = weather_data[0]["longitude"]
    folium_map = folium.Map(location=[start_lat, start_lon], zoom_start=5)
    marker_cluster = MarkerCluster().add_to(folium_map)

    for city_weather in weather_data:
        folium.Marker(
            location=[city_weather["latitude"], city_weather["longitude"]],
            popup=f"{city_weather['location']}<br>Макс. температура: {city_weather['forecast'][0]['temp_max']}°C<br>Интенсивность осадков: {city_weather['forecast'][0]['precip_intensity']}",
            tooltip=city_weather["location"],
        ).add_to(marker_cluster)

    map_html = folium_map._repr_html_()

    # вывод прогноза текстом
    weather_output = []
    for city_weather in weather_data:
        weather_output.append(html.H4(f"Прогноз для {city_weather['location']}:"))
        weather_output.append(
            html.Ul(
                [
                    html.Li(
                        f"{day['day']}: {day['condition']}, Макс. температура: {day['temp_max']}°C, Мин. температура: {day['temp_min']}°C, Интенсивность осадков: {day['precip_intensity']}"
                    )
                    for day in city_weather["forecast"]
                ]
            )
        )

    return html.Div(weather_output), fig, map_html


if __name__ == "__main__":
    app.run_server(debug=True)
