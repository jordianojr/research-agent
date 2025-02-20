from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config import settings  # Import settings here
# from agents.models import AgentDB 

async def init_db():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    await init_beanie(
        database=client[settings.DATABASE_NAME],
        document_models=[  # Dynamically import models from features
        ]
    )
    print(client.list_database_names())