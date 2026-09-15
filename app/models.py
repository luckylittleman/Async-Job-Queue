from .database import Base
from sqlalchemy.orm import mapped_column,Mapped
import enum
from typing import Dict, Any
from sqlalchemy import Column,DateTime,Enum, Integer, JSON
from datetime import datetime

class JobStatus(str, enum.Enum):
    PENDING="pending"
    IN_PROGRESS="in_progress"
    COMPLETED="completed"
    FAILED="failed"

class Job(Base):
    __tablename__="jobs"
    id: Mapped[int]=mapped_column(primary_key=True)
    status:Mapped[str]=mapped_column(
        Enum(JobStatus,values_callable=lambda x:[e.value for e in x]), 
        nullable=False, 
        default=JobStatus.PENDING,
        server_default="pending")
    priority:Mapped[int]=mapped_column(Integer, nullable=True, default=0)
    input_data:Mapped[Dict[str,Any]]=mapped_column(JSON,nullable=True)
    retry_count:Mapped[int]=mapped_column(default=0)
    max_retries:Mapped[int]=mapped_column(default=5)
    created_at:Mapped[datetime]=mapped_column(DateTime, default=datetime.now)
    started_at:Mapped[datetime]=mapped_column(DateTime, nullable=True)
    finished_at:Mapped[datetime]=mapped_column(DateTime, nullable=True)
    