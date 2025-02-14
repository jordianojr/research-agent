import sys
import os

# Ensure the project root is in sys.path so that the "app" package can be imported.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from fastapi.testclient import TestClient
from app.main import app  # Import the FastAPI app from your module

client = TestClient(app)

def test_default_route():
    response = client.get("/")
    assert response.status_code == 200
    # The app returns a plain string; FastAPI automatically converts it to JSON.
    assert response.json() == "Hello World!"

def test_create_agent():
    response = client.post("/agents")
    assert response.status_code == 200
    assert response.json() == "Create agent"

def test_get_agent():
    agent_id = "test123"
    response = client.get(f"/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json() == "Get agent"

def test_delete_agent():
    agent_id = "test123"
    response = client.delete(f"/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json() == "Delete agent"

def test_send_msg():
    agent_id = "test123"
    response = client.post(f"/agents/{agent_id}/queries")
    assert response.status_code == 200
    assert response.json() == "Send message"

def test_update_website():
    agent_id = "test123"
    response = client.put(f"/agents/{agent_id}/websites")
    assert response.status_code == 200
    assert response.json() == "Update agent websites"

def test_update_file():
    agent_id = "test123"
    response = client.put(f"/agents/{agent_id}/files")
    assert response.status_code == 200
    assert response.json() == "Update agent files"
