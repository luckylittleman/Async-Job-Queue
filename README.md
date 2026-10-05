# Async Job Queue

A FastAPI + PostgreSQL + Redis/RQ system for submitting background jobs and tracking their status via a job ID — the classic producer/consumer pattern. Built to learn async task processing, worker-based architectures, and the concurrency problems that come with multiple workers pulling from a shared queue.

**Repo:** https://github.com/luckylittleman/async-job-queue
**Live demo:** https://async-job-queue-v4it.onrender.com/docs
*(Note: free-tier hosting may spin down when idle; the first request after inactivity can take a few seconds to respond.)*

## Features

- Job submission and status tracking via a single resource (`/jobs`)
- Background job processing via Redis/RQ, with the worker running as a background thread inside the same process as the API (see **Deployment Architecture** below for why)
- Automatic retry logic with configurable `max_retries` per job
- Full job lifecycle tracking: `pending` → `in_progress` → `completed`/`failed`, with timestamps for queue wait time and execution duration
- Alembic migrations for schema versioning
- pytest suite covering both API endpoints and worker logic (including failure/retry paths via mocking)

## Tech Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy (2.0 style)
- **Migrations:** Alembic
- **Task Queue:** Redis + RQ (Redis Queue)
- **Validation:** Pydantic
- **Testing:** pytest, unittest.mock
- **Deployment:** Render (Web Service), Neon (managed Postgres), Upstash (managed Redis)

## Database Schema

A single `jobs` table holds every job's full lifecycle — status, input, retry state, and timestamps — with no separate tables per job type, since only the *content* of a job varies, not its structure.

**Job** — `id`, `status` (enum: pending/in_progress/completed/failed), `priority`, `input_data` (JSON), `retry_count`, `max_retries`, `created_at`, `started_at`, `finished_at`
Represents one unit of background work from submission through completion or permanent failure.

### Why a status-driven single table, with explicit lifecycle timestamps?

Every job shares the same structural shape regardless of what it actually does — the only thing that varies by job type is the *content* of `input_data`, which is stored as JSON rather than normalized into per-type tables. This keeps the schema simple and avoids a new migration every time a new job type is introduced. Three separate nullable timestamps (`created_at`, `started_at`, `finished_at`) — rather than a single "duration" field — make it possible to independently measure queue wait time (`started_at - created_at`) and execution time (`finished_at - started_at`), which matters for diagnosing whether a slow job is stuck waiting for a worker or actually taking a long time to run.

## API Endpoints

| Method | Path | Description | Auth required |
|---|---|---|---|
| POST | `/jobs` | Submit a new job; enqueues it for background processing | No |
| GET | `/jobs/{id}` | Retrieve a job's current status and data | No |

*This project has no authentication layer — it's scoped around the job-processing pattern itself, not access control.*

## Deployment Architecture

The live demo runs as a **single Render Web Service** rather than the two-process setup (API + separate background worker) used locally. Render's free tier doesn't include a Background Worker service type, so the RQ worker runs as a **daemon thread inside the same FastAPI process**, started on app startup:

- `SimpleWorker` (RQ's non-forking worker class) runs in a background `threading.Thread`, so job execution shares the process with the API server instead of forking a separate OS process per job.
- RQ installs OS signal handlers by default (for graceful shutdown and job-timeout enforcement) — but Python only allows signal handlers to be registered from the **main thread**, which crashes immediately in a background thread. The fix: override `_install_signal_handlers` to a no-op, and swap RQ's default signal-based job timeout (`UnixSignalDeathPenalty`, which also calls `signal.signal()`) for RQ's thread-safe alternative, `TimerDeathPenalty` (originally built for Windows, where `SIGALRM` doesn't exist — it works equally well here).
- Postgres and Redis are hosted separately (Neon and Upstash) rather than on Render's own managed databases, since Render's free tier only allows one active database instance per account, and that slot is already used by this project's predecessor (Expense Splitter).

This is a deliberate, documented tradeoff for a free-tier demo deployment — not the architecture you'd choose for a real production system, where the API and worker should scale and fail independently. Locally, the project still runs as two separate processes (`uvicorn` + `rq worker`), which is the architecture reflected in the setup instructions below.

## Design Decisions & What I Learned

- **Atomic job claiming vs. queue-based claiming:** initially designed a `SELECT ... FOR UPDATE SKIP LOCKED` pattern for workers to safely claim jobs directly from Postgres without racing each other. Once RQ was introduced, Redis itself guarantees only one worker pulls a given job ID off the queue, making that pattern unnecessary for this architecture — though it remains the correct approach for a design with no message broker at all.
- **Separating orchestration from execution:** `execute_job` (status transitions, commits, retry logic) and `do_work` (the actual task) are deliberately separate functions. This wasn't just for cleanliness — it's what made the worker's failure and retry paths testable at all, since `do_work` can be mocked to force failures on demand instead of manually editing source code before each test run.
- **Commit ordering matters for correctness, not just style:** status is committed to the database *before* any slow operation runs (e.g. `in_progress` before the actual work, `pending` before re-enqueuing a retry) — not after — so that any other process querying the job's status mid-flight sees accurate, real-time state rather than stale data.
- **Async/await was a deliberate non-choice here:** this project's actual concurrency need is *across* jobs (multiple worker processes), not *within* a single job (no job here has multiple independent slow steps worth overlapping) — so the worker code is plain synchronous Python, and RQ's lack of native async support turned out not to matter for this scope.
- **REST vs. TCP Redis endpoints are not interchangeable:** Upstash (and similar managed Redis providers) expose both a REST API (for HTTP-based SDKs) and a standard TCP connection string. RQ's Python client (`redis.from_url`) needs the TCP one (`rediss://default:...@host:6379`) — pointing it at REST credentials fails with a misleading connection error rather than an obvious "wrong endpoint type" message.

## Known Limitations / Next Steps

- **Simulated work only:** jobs currently simulate processing with a fixed delay rather than doing real work (e.g. actual image resizing). The architecture is designed to support swapping in real logic without changing the schema or pipeline.
- **Tests run against a real dev database and Redis instance**, not an isolated test environment — matching a known limitation from this project's predecessor (Expense Splitter).
- **No authentication** — out of scope for this project, which is focused on the async/queue pattern itself.

## Setup Instructions (Local Development)

1. Clone the repository and create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a PostgreSQL database and ensure a local Redis instance is running.

4. Create a `.env` file in the project root:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/job_queue_db
   REDIS_URL=redis://localhost:6379
   ```

5. Run the database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the API server:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

7. In a **separate terminal**, start the RQ worker (required — jobs will not be processed without it):
   ```bash
   rq worker
   ```

8. Visit `http://127.0.0.1:8000/docs` for interactive API documentation.

## Running Tests

Requires PostgreSQL and Redis both running (tests execute `execute_job` directly and insert real rows):

```bash
pytest
```
