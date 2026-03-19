from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Custom Tools API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    http_timeout_seconds: int = 30

    redis_url: str = "redis://localhost:6379/0"
    sqlite_path: str = "./data/custom_tools.db"
    export_dir: str = "./exports"
    youtube_max_playlist_items: int = 20
    youtube_job_timeout_seconds: int = 1200


settings = Settings()
