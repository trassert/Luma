from pathlib import Path
from typing import List, Dict
import orjson
import aiofiles


class ChatHistory:
    def __init__(
        self,
        chat_id: int,
        history_dir: Path,
        max_history: int,
        system_prompt: str,
    ):
        self.chat_id = chat_id
        self._history_dir = history_dir
        self._max_len = max_history * 2
        self._file_path = self._history_dir / f"{chat_id}.json"
        self._system_prompt = system_prompt
        self._messages: List[Dict[str, str]] = []

    async def load(self) -> None:
        self._history_dir.mkdir(exist_ok=True)
        if not self._file_path.exists():
            self._messages = []
        else:
            try:
                async with aiofiles.open(self._file_path, "rb") as f:
                    raw = await f.read()
                    self._messages = orjson.loads(raw) if raw else []
            except Exception:
                self._messages = []

        await self._ensure_system_prompt()

    async def _ensure_system_prompt(self) -> None:
        if not self._messages:
            self._messages.append({"role": "system", "content": self._system_prompt})
            return

        first_msg = self._messages[0]
        if first_msg.get("role") != "system":
            self._messages.insert(0, {"role": "system", "content": self._system_prompt})
        elif first_msg.get("content") != self._system_prompt:
            self._messages[0]["content"] = self._system_prompt

    async def save(self) -> None:
        self._history_dir.mkdir(exist_ok=True)
        if len(self._messages) > self._max_len + 1:
            user_assistant_pairs = self._messages[1:]
            trimmed = user_assistant_pairs[-self._max_len :]
            self._messages = [self._messages[0]] + trimmed

        data = orjson.dumps(self._messages)
        async with aiofiles.open(self._file_path, "wb") as f:
            await f.write(data)

    def add_user_message(self, user_name: str, text: str) -> None:
        formatted_text = f"[{user_name}] {text}"
        self._messages.append({"role": "user", "content": formatted_text})

    def add_assistant_message(self, text: str) -> None:
        self._messages.append({"role": "assistant", "content": text})

    @property
    def messages(self) -> List[Dict[str, str]]:
        return self._messages.copy()
