from redis import Redis
from rq import Queue

redis_conn=Redis(host="localhost", port=6379)
job_queue=Queue(connection=redis_conn)