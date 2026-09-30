#!/bin/bash

# Load approval rules and schemes data

BACKEND_DIR="./backend"

cd $BACKEND_DIR

python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.models import Base
from app.services.data_loader import RuleLoadingService

async def load_data():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        loader = RuleLoadingService(session)
        
        print('Loading approval rules...')
        await loader.load_approval_rules('../data/approvals/approval_rules.json')
        
        print('Loading schemes...')
        await loader.load_schemes('../data/schemes/schemes.json')
        
        print('✅ Data loaded successfully!')
    
    await engine.dispose()

asyncio.run(load_data())
"

cd ..
