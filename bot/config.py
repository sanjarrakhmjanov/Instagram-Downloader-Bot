from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids: list[int] = Field(default_factory=list, alias="ADMIN_IDS")

    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="downloader_bot", alias="POSTGRES_DB")
    postgres_user: str = Field(default="downloader", alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")

    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")

    download_dir: str = Field(default="/tmp/downloader", alias="DOWNLOAD_DIR")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_language: str = Field(default="uz", alias="DEFAULT_LANGUAGE")
    request_rate_limit: int = Field(default=10, alias="REQUEST_RATE_LIMIT")
    request_rate_window_sec: int = Field(default=60, alias="REQUEST_RATE_WINDOW_SEC")
    request_timeout_sec: int = Field(default=900, alias="REQUEST_TIMEOUT_SEC")
    max_file_size_mb: int = Field(default=49, alias="MAX_FILE_SIZE_MB")
    video_delivery_mode: str = Field(default="document", alias="VIDEO_DELIVERY_MODE")
    welcome_animation_url: str | None = Field(default=None, alias="WELCOME_ANIMATION_URL")
    welcome_image_url: str | None = Field(default=None, alias="WELCOME_IMAGE_URL")
    welcome_photo_file_id: str | None = Field(default=None, alias="WELCOME_PHOTO_FILE_ID")
    ffmpeg_path: str | None = Field(default=None, alias="FFMPEG_PATH")

    @property
    def sqlalchemy_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_dsn(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
