from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ACCUWEATHER_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    INTERNAL_WEATHER_API_URL: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def get_settings() -> Settings:
    return Settings()
