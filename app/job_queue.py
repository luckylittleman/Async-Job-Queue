from redis import Redis
from rq import Queue
import os
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_conn = Redis.from_url(redis_url)
job_queue = Queue(connection=redis_conn)