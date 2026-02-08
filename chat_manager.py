from pathlib import Path
from typing import List, Dict
import orjson
import aiofiles


class ChatHistory:
    def __init__(self, chat_id: int, history_dir: Path, max_history: int):
        self.chat_id = chat_id
        self._history_dir = history_dir
        self._max_len = max_history * 2
        self._file_path = self._history_dir / f"{chat_id}.json"
        self._messages: List[Dict[str, str]] = []

    async def load(self) -> None:
        self._history_dir.mkdir(exist_ok=True)
        if not self._file_path.exists():
            self._messages = []
            return
        try:
            async with aiofiles.open(self._file_path, "rb") as f:
                raw = await f.read()
                self._messages = orjson.loads(raw) if raw else []
        except Exception:
            self._messages = []

    async def save(self) -> None:
        self._history_dir.mkdir(exist_ok=True)
        trimmed = self._messages[-self._max_len :]
        data = orjson.dumps(trimmed)
        async with aiofiles.open(self._file_path, "wb") as f:
            await f.write(data)

    def add_user_message(self, text: str) -> None:
        self._messages.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str) -> None:
        self._messages.append({"role": "assistant", "content": text})

    @property
    def messages(self) -> List[Dict[str, str]]:
        return self._messages.copy()
