import pytest
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.fixture(autouse=True)
async def reset_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await client.drop_database("test_db")
    await init_mongo()