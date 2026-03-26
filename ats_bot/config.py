from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    discord_bot_token: str = os.getenv("DISCORD_BOT_TOKEN", "")
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.4")
    output_dir: Path = Path(os.getenv("OUTPUT_DIR", "outputs")).resolve()
    public_file_base_url: str = os.getenv("PUBLIC_FILE_BASE_URL", "").rstrip("/")


settings = Settings()
settings.output_dir.mkdir(parents=True, exist_ok=True)
