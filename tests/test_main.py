from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import Job
from app.worker import execute_job
from unittest.mock import patch
from datetime import datetime


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

def test_job_with_non_exitent_id():
    response=client.get("/jobs/0")
    assert response.status_code == 404
    assert response.json()["detail"] == "Job not found"

def test_job_retries():
    with SessionLocal() as session:
        new_job=Job(
            input_data={"type":"test"},
            priority=0,
            max_retries=2
        )
        session.add(new_job)
        session.commit()
        session.refresh(new_job)
       
        job_id=new_job.id
    with patch("app.worker.do_work", side_effect=Exception("Forced Failure")):
        execute_job(job_id)

    with SessionLocal() as session:
        job=session.query(Job).filter(Job.id==job_id).first()
        assert job.status == "pending"
        assert job.retry_count == 1


def test_permanet_failure():
    with SessionLocal() as session:
        new_job=Job(
            input_data={"type":"test"},
            priority=0,
            max_retries=1
        )
        session.add(new_job)
        session.commit()
        session.refresh(new_job)
       
        job_id=new_job.id
    with patch("app.worker.do_work", side_effect=Exception("Forced Failure")):
        execute_job(job_id)

    with SessionLocal() as session:
        job=session.query(Job).filter(Job.id==job_id).first()
        assert job.status == "failed"
        assert job.retry_count == 1



def test_job_completion():
    with SessionLocal() as session:
        new_job=Job(
            input_data={"type":"test"},
            priority=0,
            max_retries=1
        )
        session.add(new_job)
        session.commit()
        session.refresh(new_job)
       
        job_id=new_job.id

    execute_job(job_id)
    
    with SessionLocal() as session:
        job=session.query(Job).filter(Job.id==job_id).first()
        assert job.status == "completed"
        assert job.retry_count == 0
        assert job.finished_at is not None




   