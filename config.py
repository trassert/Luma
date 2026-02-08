from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    bot_token = ""
    groq_api_key = ""
    history_dir = Path("history")
    max_history = 15
    groq_model = "qwen/qwen3-32b"
