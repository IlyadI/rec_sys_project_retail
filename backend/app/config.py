from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    user_purchases_path: str = "backend/data/user_purchases.json"
    product_embeddings_path: str = "backend/data/product_embeddings.json"

    # LLM (Cloud.ru Foundation Models)
    foundation_models_api_key: str = Field(default="", validation_alias="API_KEY")
    foundation_models_base_url: str = Field(
        default="https://foundation-models.api.cloud.ru/v1",
        validation_alias="FOUNDATION_MODELS_BASE_URL",
    )
    # ЧАТ-МОДЕЛЬ ДЛЯ ТЕКСТОВЫХ ОБЪЯСНЕНИЙ
    foundation_models_chat_model: str = Field(
        default="openai/gpt-oss-120b",
        validation_alias="FOUNDATION_MODELS_CHAT_MODEL",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
