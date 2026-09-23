from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    debug: bool = False
    allow_origins: str = "https://baraholka.org"

    api_id: int = 223123123
    api_hash: str = "jfosbfoubfu9b97347823f47vu"
    phone_number: str = "+3751212312312"
    session_string: str = ""

    mongo_url: str = "mongodb://root:example@localhost:27017"
    mongo_db_name: str = "baraholka"

    scheduler_interval_seconds: int = 100

    log_level: str = "INFO"

    openai_api_key: str = ""
    telegram_bot_token: str = ""

    messages_batch_size: int = 100


settings = Settings()
