from fastapi.testclient import TestClient
from backend.blog_fastapi import app

client = TestClient(app)

def test_home_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["msg"] == "api is running"