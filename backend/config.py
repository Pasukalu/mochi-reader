"""Configuration is read only on the server; credentials never enter the browser."""

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    database: str
    api_key: str
    api_base: str
    model: str
    cors_origins: tuple[str, ...]

    @property
    def mode(self) -> str:
        return "live" if self.api_key else "demo"


def settings_from_env() -> Settings:
    base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    url = urlparse(base)
    if url.scheme != "https" and not (
        url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        raise ValueError("DEEPSEEK_BASE_URL must use HTTPS or a loopback HTTP server")
    if not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("DEEPSEEK_BASE_URL must be a plain API base URL")
    origins = tuple(
        item.strip()
        for item in os.getenv(
            "MOCHI_CORS_ORIGINS", "http://127.0.0.1:8765,http://localhost:8765"
        ).split(",")
        if item.strip()
    )
    if "*" in origins or "null" in origins:
        raise ValueError("MOCHI_CORS_ORIGINS requires explicit origins")
    return Settings(
        database=os.getenv("MOCHI_DB_PATH", str(ROOT / "data" / "mochi.sqlite3")),
        api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        api_base=base,
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        cors_origins=origins,
    )
