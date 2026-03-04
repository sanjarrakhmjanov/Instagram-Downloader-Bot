import asyncio

from bot.db.session import init_db


if __name__ == "__main__":
    asyncio.run(init_db())

