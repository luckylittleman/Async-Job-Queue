from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from .schemas import JobCreate, JobOut
from .models import Job
from .job_queue import job_queue
from .worker import execute_job
import threading
from rq import SimpleWorker
from rq.timeouts import TimerDeathPenalty
from .job_queue import redis_conn


app=FastAPI()
class ThreadSafeWorker(SimpleWorker):
    death_penalty_class = TimerDeathPenalty

def start_worker():
    worker = ThreadSafeWorker(["default"], connection=redis_conn)
    worker._install_signal_handlers = lambda: None
    worker.work()

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=start_worker, daemon=True)
    thread.start()

@app.get("/")
def project_root():
    return {"message":"Welcome to the Async-Job-Queue backend, head over to /docs to view the endpoints"}

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
    job_queue.enqueue(execute_job,new_job.id)
    return new_job

@app.get("/jobs/{id}", response_model=JobOut)
def get_job(id:int, db:Session=Depends(get_db)):
    job=db.query(Job).filter(Job.id==id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
