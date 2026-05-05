from ipaddress import IPv4Network, IPv6Network, ip_network
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Network = IPv4Network | IPv6Network


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    asus_host: str = "192.168.50.1"
    asus_user: str = "admin"
    asus_pass: str = ""
    asus_use_ssl: bool = True
    asus_verify_ssl: bool = False

    # NoDecode disables pydantic-settings' default JSON decoding for list fields,
    # so we receive the raw env string and split it ourselves below.
    lan_cidrs: Annotated[
        list[Network],
        NoDecode,
        Field(default_factory=lambda: [ip_network("192.168.50.0/24")]),
    ]
    cooldown_seconds: int = 300

    listen_host: str = "0.0.0.0"
    listen_port: int = 8080
    log_level: str = "INFO"

    @field_validator("lan_cidrs", mode="before")
    @classmethod
    def _split_cidrs(cls, v: object) -> list[Network] | object:
        if isinstance(v, str):
            return [ip_network(s.strip(), strict=False) for s in v.split(",") if s.strip()]
        return v


def get_settings() -> Settings:
    return Settings()
