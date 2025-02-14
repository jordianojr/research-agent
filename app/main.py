from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def default():
    return("Hello World!")

@app.post("/agents")
def create_agent():
    return("Create agent")

@app.get("/agents/{agent_id}")
def get_agent():
    return("Get agent")

@app.delete("/agents/{agent_id}")
def delete_agent():
        return("Delete agent")
    
@app.post("/agents/{agent_id}/queries")
def send_msg():
    return("Send message")

@app.put("/agents/{agent_id}/websites")
def update_website():
    return("Update agent websites")

@app.put("/agents/{agent_id}/files")
def update_file():
    return("Update agent files")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
