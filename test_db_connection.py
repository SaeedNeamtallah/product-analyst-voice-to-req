import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def test():
    url = "postgresql+asyncpg://ragmind:ragmind123@localhost:5435/ragmind"
    print(f"Testing connection to: {url}")
    e = create_async_engine(url)
    async with e.begin() as c:
        r = await c.execute(text('SELECT 1'))
        print('Connected!', r.fetchone())
    await e.dispose()

asyncio.run(test())
