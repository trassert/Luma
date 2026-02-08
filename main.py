import uvloop
import orjson
import aiofiles
from pathlib import Path
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import Command
from aiohttp import ClientSession
from config import Config
from chat_manager import ChatHistory

router = Router()

SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.txt"


async def load_system_prompt() -> str:
    if not SYSTEM_PROMPT_PATH.exists():
        return "Ты — полезный ассистент."
    async with aiofiles.open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        return (await f.read()).strip()


class AIChatBot:
    def __init__(self, config: Config):
        self.config: Config = config

    async def handle(self, message: Message, session: ClientSession) -> None:
        user_text = message.text.partition(" ")[2].strip()
        if not user_text:
            await message.reply("💬 Напиши что-нибудь после /ии")
            return

        chat_id = message.chat.id
        history = ChatHistory(chat_id, self.config.history_dir, self.config.max_history)
        await history.load()
        history.add_user_message(user_text)

        payload = {
            "model": self.config.groq_model,
            "messages": history.messages,
            "temperature": 0.7,
            "max_tokens": 512,
        }

        headers = {
            "Authorization": f"Bearer {self.config.groq_api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with session.post(
                "https://api.groq.com/openai/v1/chat/completions",
                data=orjson.dumps(payload),
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    await message.reply(f"⚠️ Groq error: {resp.status}\n{error_text}")
                    return

                data = orjson.loads(await resp.read())
                reply_text = data["choices"][0]["message"]["content"].strip()

            history.add_assistant_message(reply_text)
            await history.save()
            await message.reply(reply_text)

        except Exception as e:
            await message.reply(f"💥 Ошибка: {str(e)}")


@router.message(Command("ии", ignore_case=True))
async def command_ai(
    message: Message, bot: Bot, session: ClientSession, ai_bot: AIChatBot
):
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
