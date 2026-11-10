"""Server-side persistence; saved credentials are never returned by settings APIs."""

import json
import os
import re
import tempfile
import warnings
from dataclasses import dataclass, replace
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
    settings_path: str = ""

    @property
    def mode(self) -> str:
        return "live" if self.api_key else "demo"


def validate_api_base(value: str) -> str:
    base = value.strip().rstrip("/")
    if not base or len(base) > 2048 or any(char.isspace() or ord(char) < 32 for char in base):
        raise ValueError("API 地址无效，请使用不带空格的 HTTPS 地址。")
    url = urlparse(base)
    if url.scheme != "https" and not (
        url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        raise ValueError("API 地址须使用 HTTPS；仅本机 localhost/127.0.0.1 可使用 HTTP。")
    if not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("API 地址不能包含账号、密码、查询参数或锚点。")
    try:
        port = url.port
    except ValueError as exc:
        raise ValueError("API 地址端口无效。") from exc
    if port == 0:
        raise ValueError("API 地址端口无效。")
    # IDNA-encode the host while preserving the provider's case-sensitive path.
    try:
        hostname = url.hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValueError("API 地址主机名无效。") from exc
    host = f"[{hostname}]" if ":" in hostname else hostname
    return f"{url.scheme}://{host}{f':{port}' if port is not None else ''}{url.path.rstrip('/')}"


def validate_model(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", value):
        raise ValueError("模型名须为 1 至 200 个字母、数字或 . _ : / -，不能含空格。")
    return value


def validate_api_key(value: str) -> str:
    value = value.strip()
    if len(value) > 4096 or any(not 33 <= ord(char) <= 126 for char in value):
        raise ValueError("API key 格式无效，请粘贴不含空格或换行的密钥。")
    return value


def provider_origin(base: str) -> tuple[str, str, int]:
    parsed = urlparse(base)
    return parsed.scheme, parsed.hostname.lower(), parsed.port or (443 if parsed.scheme == "https" else 80)


def settings_file(settings: Settings) -> Path:
    return Path(settings.settings_path) if settings.settings_path else Path(settings.database).resolve().parent / "provider-settings.json"


def load_provider_settings(settings: Settings) -> Settings:
    """Saved settings override env defaults, including an explicitly empty key."""
    path = settings_file(settings)
    if not path.exists():
        return settings
    try:
        if path.stat().st_size > 20000:
            raise ValueError("Settings file too large")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("version") != 1 or any(
            not isinstance(data.get(key), str) for key in ("api_base", "api_key", "model")
        ):
            raise ValueError("Invalid settings file")
        return replace(settings, api_base=validate_api_base(data["api_base"]),
                       model=validate_model(data["model"]), api_key=validate_api_key(data["api_key"]))
    except (OSError, ValueError, UnicodeError):
        # Never print the file content or key when recovering from bad local data.
        warnings.warn("本机模型设置文件无法读取；已使用环境默认值，请在设置中重新保存。", RuntimeWarning)
        return settings


def save_provider_settings(settings: Settings) -> None:
    """Atomically replace a local-only, private-permission settings file."""
    path = settings_file(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "api_base": settings.api_base, "model": settings.model, "api_key": settings.api_key}
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix=".provider-settings-", suffix=".tmp", dir=path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def settings_from_env() -> Settings:
    base = validate_api_base(os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
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
        api_key=validate_api_key(os.getenv("DEEPSEEK_API_KEY", "")),
        api_base=base,
        model=validate_model(os.getenv("DEEPSEEK_MODEL", "deepseek-flash")),
        cors_origins=origins,
        settings_path=os.getenv("MOCHI_SETTINGS_PATH", ""),
    )
