from .database import SessionLocal
from .models import Job, JobStatus
from datetime import datetime
import time
from .job_queue import job_queue




def execute_job(job_id:int):
    with SessionLocal() as session:
        job=session.query(Job).filter(Job.id==job_id).first()
        job.status=JobStatus.IN_PROGRESS
        job.started_at=datetime.now()
        session.commit()
        try:
         
         time.sleep(5)
         job.status= JobStatus.COMPLETED
         job.finished_at=datetime.now()
        except Exception as e:
           print(e)
           job.retry_count+=1
           if job.retry_count < job.max_retries:
              job.status=JobStatus.PENDING
              session.commit()
              job_queue.enqueue(execute_job,job.id)
           else:
              job.status=JobStatus.FAILED
              job.finished_at=datetime.now()
                 
        session.commit()
        

    return job


