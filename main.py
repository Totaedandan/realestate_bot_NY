import asyncio
from app.bot import build_dispatcher, build_bot
from app.db import init_db

async def main() -> None:
    await init_db()
    bot = build_bot()
    dp = build_dispatcher(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
