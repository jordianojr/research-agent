from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from agents.agent import begin_research
from agents.webscrape import scraper
from datetime import datetime
import os

app = FastAPI()
db = None

class AgentDB(BaseModel):
    id: str = Field(alias="_id")
    name: str
    files: List[Dict] = []
    websites: List[Dict] = []
    messages: List[Dict] = []

class Message(BaseModel):
    message: str
    
async def init_db():
    global db
    try:
        # Use environment variable or fallback to default
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        client = AsyncIOMotorClient(mongodb_url)
        db = client.agents_db
        await client.admin.command('ping')
        print("Successfully connected to MongoDB!")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        raise e

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post(
    "/agents",
    status_code=201,
    responses={
        201: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {"additionalProp1": "string"}
                }
            }
        }
    }
)
async def create_agent(agent_post: str = Form(...), files: Optional[List[UploadFile]] = None):
    try:
        # Parse the agent_post string into a dict
        agent_data = json.loads(agent_post)
        print(f"Received agent data: {agent_data}")  # Debug log
        
        # Create new agent document
        agent = {
            "name": agent_data["name"],
            "files": [],
            "websites": [],
            "messages": []
        }
        print(f"Created agent document: {agent}")  # Debug log
        
        # Insert into MongoDB
        try:
            result = await db.agents.insert_one(agent)
            agent_id = str(result.inserted_id)
            print(f"Successfully inserted agent with ID: {agent_id}")  # Debug log
        except Exception as e:
            print(f"MongoDB insertion error: {e}")  # Debug log
            raise
        
        # Process files if they exist
        if files:
            print(f"Processing {len(files)} files")  # Debug log
            for file in files:
                contents = await file.read()
                await db.agents.update_one(
                    {"_id": ObjectId(agent_id)},
                    {"$push": {"files": {
                        "filename": file.filename,
                        "content_type": file.content_type,
                        "content": contents.decode()
                    }}}
                )
        
        return {"additionalProp1": agent_id}
    except Exception as e:
        print(f"Error in create_agent: {e}")  # Debug log
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/{agent_id}", response_model=AgentDB)
async def get_agent(agent_id: str):
    try:
        agent = await db.agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        # Convert ObjectId to string for JSON serialization
        agent["_id"] = str(agent["_id"])
        return agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: str):
    try:
        result = await db.agents.delete_one({"_id": ObjectId(agent_id)})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/{agent_id}/queries", status_code=201)
async def send_message(agent_id: str, message: Message):
    try:
        # Check if agent exists
        agent = await db.agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Run the research process and get the final draft
        final_draft = begin_research(message.message)

        # Store the result in MongoDB
        await db.agents.update_one(
            {"_id": ObjectId(agent_id)},
            {"$push": {"messages": {
                "query": message.message,
                "response": final_draft,
                "timestamp": datetime.utcnow()
            }}}
        )

        # Return the draft in the expected format
        return {
            "response": final_draft
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.put("/agents/{agent_id}/websites", status_code=204)
async def update_agent_websites(agent_id: str, websites: List[str]):
    try:
        # Check if agent exists
        agent = await db.agents.find_one({"_id": ObjectId(agent_id)})
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        # Process websites using the WebScraper
        processed_websites = scraper.process_websites(websites)
        
        # Update agent's websites in MongoDB
        if processed_websites:
            await db.agents.update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": {"websites": processed_websites}}
            )
        
        return None

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/agents/{agent_id}/files", status_code=204)
async def update_agent_files(agent_id: str, files: List[UploadFile] = File(...)):
    # Implementation for updating agent files
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

