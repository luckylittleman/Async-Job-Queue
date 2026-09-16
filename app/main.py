from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .schemas import JobCreate, JobOut
from .models import Job

app=FastAPI()

@app.post("/jobs", response_model=JobOut, status_code=201)
def create_job(job:JobCreate, db:Session=Depends(get_db)):
    new_job=Job(
        input_data=job.input_data,
        priority=job.priority,
        max_retries=job.max_retries
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@app.get("/jobs/{id}", response_model=JobOut)
def get_job(id:int, db:Session=Depends(get_db)):
    job=db.query(Job).filter(Job.id==id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
