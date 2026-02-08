from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Config:
    bot_token: str
    groq_api_key: str
    history_dir: Path
    max_history: int
    groq_model: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            bot_token=os.environ["BOT_TOKEN"],
            groq_api_key=os.environ["GROQ_API_KEY"],
            history_dir=Path(os.environ.get("HISTORY_DIR", "./chat_histories")).resolve(),
            max_history=int(os.environ.get("MAX_HISTORY", "10")),
            groq_model=os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),
        )