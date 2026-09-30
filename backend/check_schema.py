import asyncio

from sqlalchemy import text

from app.core.database import engine
from app.models import Approval


async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='approvals' ORDER BY ordinal_position"))
        cols = [r[0] for r in result]
        print('approvals columns:', cols)
        print('Approval model columns:', [c.name for c in Approval.__table__.columns])

asyncio.run(check())