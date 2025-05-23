import json
import os
from dataclasses import dataclass, field
from typing import List

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


class RabbitMQSettings(BaseSettings):
    url: str = "amqp://guest:guest@rabbitmq:5672/"

    model_config = SettingsConfigDict(
        env_prefix="rabbitmq_", env_file_encoding="utf-8", extra="ignore"
    )


class EncryptionSettings(BaseSettings):
    key: str

    model_config = SettingsConfigDict(
        env_prefix="encryption_", env_file_encoding="utf-8", extra="ignore"
    )


class S3Settings(BaseSettings):
    endpoint_url: str
    access_key: str
    secret_key: str
    region: str
    bucket_name: str

    model_config = SettingsConfigDict(
        env_prefix="s3_", env_file_encoding="utf-8", extra="ignore"
    )


class UserGrpcSettings(BaseSettings):
    host: str
    port: int

    model_config = SettingsConfigDict(
        env_prefix="user_grpc_", env_file_encoding="utf-8", extra="ignore"
    )


class AIGrpcSettings(BaseSettings):
    host: str
    port: int

    model_config = SettingsConfigDict(
        env_prefix="ai_grpc_", env_file_encoding="utf-8", extra="ignore"
    )


class AppSettings(BaseSettings):
    allow_origins: str = ""

    @property
    def allowed_origins(self) -> List[str]:
        return [
            origin.strip() for origin in self.allow_origins.split(";") if origin.strip()
        ]

    model_config = SettingsConfigDict(
        env_prefix="", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@dataclass
class Settings:
    jwt_settings: JWTSettings = field(default_factory=JWTSettings)
    rabbitmq_settings: RabbitMQSettings = field(default_factory=RabbitMQSettings)
    encryption_settings: EncryptionSettings = field(default_factory=EncryptionSettings)
    s3_settings: S3Settings = field(default_factory=S3Settings)
    user_service: UserGrpcSettings = field(default_factory=UserGrpcSettings)
    ai_service: AIGrpcSettings = field(default_factory=AIGrpcSettings)
    allowed_origins: list[str] = field(
        default_factory=lambda: AppSettings().allowed_origins
    )


settings = Settings()

NOTIFICATIONS = {}

NOTIFICATIONS_PATH = os.path.join(BASE_DIR, "data", "notifications.json")

if os.path.exists(NOTIFICATIONS_PATH):
    with open(NOTIFICATIONS_PATH, encoding="utf-8") as f:
        NOTIFICATIONS = json.load(f)
