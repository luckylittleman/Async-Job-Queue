from fastapi.testclient import TestClient
from app.main import app


client=TestClient(app)

def test_job_creation():
    response=client.post("/jobs", json={"input_data":{"type":"test"}})
    assert response.status_code== 201
    data=response.json()
    assert data["status"] == "pending"
    assert data["retry_count"] == 0
    assert data["max_retries"] == 5

def test_job_retrival():
    response=client.post("/jobs", json={"input_data":{"type":"test"}})
    data=response.json()
    get_id=data["id"]
    response2=client.get(f"/jobs/{get_id}")
    assert response2.status_code == 200
    data2=response2.json()
    assert data2["status"] == "pending"
    assert data2["id"] == get_id



   