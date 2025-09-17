from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


# Load environment variables from a local .env if present (harmless in containers)
load_dotenv()


@dataclass(frozen=True)
class Settings:
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_chat_deployment_name: str
    azure_openai_api_version: Optional[str] = None
    chat_db_path: str = "./data/chat.db"
    max_history_turns: int = 10


def get_settings() -> Settings:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_OPEN_AI__ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPEN_AI__API_KEY")
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME") or os.getenv(
        "AZURE_OPEN_AI__CHAT_COMPLETION_DEPLOYMENT_NAME"
    )
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    chat_db_path = os.getenv("CHAT_DB_PATH", "./data/chat.db")
    try:
        max_history_turns = int(os.getenv("MAX_HISTORY_TURNS", "10"))
    except ValueError:
        max_history_turns = 10

    missing = [
        name
        for name, value in {
            "AZURE_OPENAI_ENDPOINT": endpoint,
            "AZURE_OPENAI_API_KEY": api_key,
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME": deployment,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

    return Settings(
        azure_openai_endpoint=endpoint,
        azure_openai_api_key=api_key,
        azure_openai_chat_deployment_name=deployment,
        azure_openai_api_version=api_version,
        chat_db_path=chat_db_path,
        max_history_turns=max_history_turns,
    )
