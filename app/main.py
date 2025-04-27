from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi
from bson import ObjectId
from agents.agent import begin_research
from agents.webscrape import scraper
from agents.file_extractor import file_processor
from datetime import datetime
import uvicorn
import os
import logging

app = FastAPI()
db = None

# Add startup state tracking
app.state.is_ready = False

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
        # MongoDB Atlas connection string
        mongodb_url = os.getenv("MONGODB_URL", "mongodb+srv://admin:<db_password>@research-agent.ccvfnie.mongodb.net/?retryWrites=true&w=majority&appName=research-agent")
        # Create a new client and connect to the server with ServerApi=1
        client = AsyncIOMotorClient(mongodb_url, server_api=ServerApi('1'), serverSelectionTimeoutMS=5000)
        db = client.agents_db
        await client.admin.command('ping')
        print("Successfully connected to MongoDB Atlas!")
        return True
    except Exception as e:
        print(f"Error connecting to MongoDB Atlas: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    db_success = await init_db()
    if db_success:
        app.state.is_ready = True
    else:
        # Still mark as ready if DB fails, as it might be optional for some endpoints
        app.state.is_ready = True
        print("Warning: Application starting without database connection")

@app.get("/_health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    if not app.state.is_ready:
        raise HTTPException(status_code=503, detail="Application is not ready")
    return {"status": "healthy"}

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
        final_draft = begin_research(task=message.message, agent_db=agent)

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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/agents/{agent_id}/files", status_code=204)
async def update_agent_files(agent_id: str, files: List[UploadFile] = File(...)):
    try:
        # Log the incoming request
        logging.info(f"Received file upload request for agent {agent_id}")
        logging.info(f"Number of files: {len(files)}")
        
        # Check if agent exists
        agent = await db.agents.find_one({"_id": ObjectId(agent_id)})
        if agent is None:  # Changed from 'if not agent'
            logging.error(f"Agent {agent_id} not found")
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Initialize file processor's database connection
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        await file_processor.init_db(mongodb_url)
        
        # Process and store files
        logging.info("Starting file processing")
        await file_processor.process_files(agent_id, files)
        logging.info("File processing completed successfully")
        
        return None
    except ValueError as e:
        logging.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.error(f"Error processing files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

