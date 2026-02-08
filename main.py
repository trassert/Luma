import uvloop
import orjson
import aiofiles
import asyncio
from time import time
from pathlib import Path
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiohttp import ClientSession
from config import Config
from chat_manager import ChatHistory
from md import markdown_to_telegram_v2, split_message

router = Router()

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.txt"


class FloodWaitBase:
    def __init__(
        self,
        name="FloodWaitSys",
        timer=5,
        exit_multiplier=3,
        lasttime=time(),
    ) -> None:
        self.time = lasttime
        self.timer = timer
        self.exit_multiplier = exit_multiplier

    def request(self):
        now = time()
        elapsed = now - self.time
        if elapsed >= self.timer:  # Разрешать сразу, если прошло достаточно
            self.time = now
            return 0
        wait_time = self.timer - elapsed
        if wait_time > self.timer * self.exit_multiplier:  # Тасккилл если овер запросов
            return False
        self.time = now + wait_time
        return round(wait_time)  # Возвращаем флудвайт, с уч. будущего


FloodWait = FloodWaitBase("WaitAI", 20)


async def load_system_prompt() -> str:
    if not SYSTEM_PROMPT_PATH.exists():
        return "Ты — полезный ассистент."
    async with aiofiles.open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        return (await f.read()).strip()


class AIChatBot:
    def __init__(self, config: Config, system_prompt: str):
        self.config = config
        self.system_prompt = system_prompt

    async def handle(self, message: Message, session: ClientSession) -> None:
        user_text = message.text.partition(" ")[2].strip()
        if not user_text:
            return

        chat_id = message.chat.id
        history = ChatHistory(
            chat_id=chat_id,
            history_dir=self.config.history_dir,
            max_history=self.config.max_history,
            system_prompt=self.system_prompt,
        )
        await history.load()
        user_name = (
            message.from_user.full_name
            or message.from_user.username
            or f"user_{message.from_user.id}"
        )
        history.add_user_message(user_name, user_text)

        payload = {
            "model": self.config.groq_model,
            "messages": history.messages,
            "temperature": 0.7,
            "max_tokens": 512,
            "reasoning_effort": "none",
        }

        headers = {
            "Authorization": f"Bearer {self.config.groq_api_key}",
            "Content-Type": "application/json",
        }

        async with session.post(
            "https://api.groq.com/openai/v1/chat/completions",
            data=orjson.dumps(payload),
            headers=headers,
        ) as resp:

            data = orjson.loads(await resp.read())
            reply_text = data["choices"][0]["message"]["content"].strip()

        history.add_assistant_message(reply_text)
        await history.save()
        text = markdown_to_telegram_v2(reply_text)
        if len(text) > 4096:
            text = split_message(text)
            message = await message.edit_text(text[0], parse_mode=ParseMode.MARKDOWN_V2)
            text.pop(0)
            for chunk in text:
                message = await message.reply(chunk, parse_mode=ParseMode.MARKDOWN_V2)
            return
        return await message.edit_text(text, parse_mode=ParseMode.MARKDOWN_V2)


@router.message(Command("ии", ignore_case=True))
async def command_ai(
    message: Message, bot: Bot, session: ClientSession, ai_bot: AIChatBot
):
    if message.chat.id not in Config.chats:
        return
    response = FloodWait.request()
    if response is False:
        return
    if response > 0:
        message = await message.reply(f"⏳ В очереди.. ({response} сек.)")
        await asyncio.sleep(response)
    else:
        message = await message.reply("Генерирую ответ..")
    await ai_bot.handle(message, session)


async def main():
    system_prompt = await load_system_prompt()
    bot = Bot(token=Config.bot_token)
    dp = Dispatcher()
    dp.include_router(router)

    ai_bot = AIChatBot(Config, system_prompt)

    async with ClientSession() as session:
        dp.workflow_data.update(
            {
                "session": session,
                "ai_bot": ai_bot,
            }
        )
        await dp.start_polling(bot, session=session, ai_bot=ai_bot)


if __name__ == "__main__":
    uvloop.run(main())
