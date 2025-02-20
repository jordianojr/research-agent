from pydantic_settings import BaseSettings
import pymongo

class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://127.0.0.1:27017"
    DATABASE_NAME: str = "research_agents"

    class Config:
        env_file = ".env"

settings = Settings()