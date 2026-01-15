import asyncio
from app.bot import build_dispatcher, build_bot
from app.db import init_db


async def main() -> None:
    await init_db()
    bot = build_bot()

    # На всякий случай убираем webhook, чтобы polling точно получал апдейты
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    dp = build_dispatcher(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
