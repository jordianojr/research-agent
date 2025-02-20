import sys
import os
import json
from fastapi.testclient import TestClient
from fastapi import UploadFile
from io import BytesIO

# Ensure the project root is in sys.path so that the "app" package can be imported.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app  # Import the FastAPI app from your module

client = TestClient(app)

def test_create_agent():
    # Create a mock file for testing
    mock_file = UploadFile(filename="test.txt", file=BytesIO(b"test content"))
    
    response = client.post(
        "/agents",
        data={"agent_post": json.dumps({"name": "Test Agent"})},
        files={"files": ("test.txt", mock_file.file, "text/plain")}
    )
    assert response.status_code == 201
    assert "agent_id" in response.json()

def test_get_agent():
    agent_id = "test123"
    response = client.get(f"/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Sample Agent"
    assert response.json()["_id"] == agent_id

def test_delete_agent():
    agent_id = "test123"
    response = client.delete(f"/agents/{agent_id}")
    assert response.status_code == 204

def test_update_agent_websites():
    agent_id = "test123"
    websites = ["https://example.com", "https://test.com"]
    response = client.put(f"/agents/{agent_id}/websites", json=websites)
    assert response.status_code == 204

def test_update_agent_files():
    agent_id = "test123"
    # Create mock files for testing
    mock_file1 = UploadFile(filename="test1.txt", file=BytesIO(b"test content 1"))
    mock_file2 = UploadFile(filename="test2.txt", file=BytesIO(b"test content 2"))
    
    response = client.put(
        f"/agents/{agent_id}/files",
        files=[
            ("files", ("test1.txt", mock_file1.file, "text/plain")),
            ("files", ("test2.txt", mock_file2.file, "text/plain"))
        ]
    )
    assert response.status_code == 204

def test_send_message():
    agent_id = "test123"
    message = {"message": "Hello, agent!"}
    response = client.post(f"/agents/{agent_id}/queries", json=message)
    assert response.status_code == 201
    assert "response" in response.json()

if __name__ == "__main__":
    import pytest
    pytest.main([__file__])
