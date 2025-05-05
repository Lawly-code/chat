import os
from dataclasses import dataclass, field

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class JWTSettings(BaseSettings):
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_minutes: int

    model_config = SettingsConfigDict(
        env_prefix="jwt_", env_file_encoding="utf-8", extra="ignore"
    )


class RedisSettings(BaseSettings):
    url: str = "redis://redis:6379/0"
    
    model_config = SettingsConfigDict(
        env_prefix="redis_", env_file_encoding="utf-8", extra="ignore"
    )


class RabbitMQSettings(BaseSettings):
    url: str = "amqp://guest:guest@rabbitmq:5672/"
    
    model_config = SettingsConfigDict(
        env_prefix="rabbitmq_", env_file_encoding="utf-8", extra="ignore"
    )


@dataclass
class Settings:
    jwt_settings: JWTSettings = field(default_factory=JWTSettings)
    redis_settings: RedisSettings = field(default_factory=RedisSettings)
    rabbitmq_settings: RabbitMQSettings = field(default_factory=RabbitMQSettings)


settings = Settings()
