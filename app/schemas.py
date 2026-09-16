from pydantic import BaseModel
from typing import Dict
from datetime import datetime

class JobCreate(BaseModel):
    input_data:Dict
    priority:int | None=0
    max_retries:int | None=5
    
    


class JobOut(BaseModel):
    input_data:Dict
    priority:int
    max_retries:int
    id:int
    status:str
    retry_count:int
    created_at:datetime
    started_at:datetime | None
    finished_at:datetime | None
