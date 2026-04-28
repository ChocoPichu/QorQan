# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from handlers import router

# YOUR TOKEN
TOKEN = "8775118314:AAGJ68_tS4DpUX3PfHhx8JpGBhUnQoCxZ6U"


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    print("Bot is running: t.me/QorganQorkakBot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")