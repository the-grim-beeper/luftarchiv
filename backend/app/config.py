from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://luftarchiv:luftarchiv_dev@localhost:5435/luftarchiv"
    anthropic_api_key: str = ""
    image_storage_path: str = "./data/images"

    model_config = {"env_file": ".env"}


settings = Settings()
