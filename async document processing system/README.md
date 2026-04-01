# Async CSV Profiling Workflow System

Production-style full stack application for uploading CSV files, triggering asynchronous profiling jobs, tracking live progress, reviewing profiling output, and exporting results.

## Overview

This project implements the assignment as a CSV-focused document processing workflow. A user uploads a CSV file as a project, starts a profiling run, and the backend processes it asynchronously using Celery. Redis is used both as the Celery broker/backend and as the Pub/Sub channel for live progress events. The frontend listens to those updates through an SSE bridge and renders profiling results once the run is complete.

## Tech Stack

- Frontend: Next.js + TypeScript
- Backend: FastAPI + Python
- Database: PostgreSQL
- Background processing: Celery
- Messaging / state: Redis
- Data profiling: pandas + NumPy + ppscore

## Implemented Features

- Create project with CSV upload
- Save project metadata in PostgreSQL
- Create profiling runs per project
- Process runs asynchronously with Celery
- Publish progress events from worker through Redis Pub/Sub
- Stream progress updates to frontend using SSE
- Show run status and progress on the detail page
- Generate profiling output for:
  - numeric stats
  - categorical stats
  - date stats
  - correlation stats
  - PPS stats
- Show correlation and PPS as heatmaps
- Export run results as JSON
- Export run results as CSV
- Workspace search
- Workspace filter by status
- Workspace sorting

## Architecture

### Backend

- `backend/app/api/routes/projects.py`
  - project CRUD endpoints
  - run creation endpoint
- `backend/app/api/routes/runs.py`
  - run status
  - SSE progress stream
  - metrics
  - export
- `backend/app/services/profiling_service.py`
  - pandas-based profiling logic
- `backend/app/workers/tasks.py`
  - Celery task execution
  - run state updates
  - profiling result persistence
- `backend/app/workers/progress.py`
  - Redis Pub/Sub publisher for run progress events

### Frontend

- `frontend/src/app/page.tsx`
  - landing page
- `frontend/src/app/workspace/page.tsx`
  - dashboard
  - create project
  - search/filter/sort
- `frontend/src/app/workspace/[projectId]/page.tsx`
  - start profiling run
  - live progress
  - metrics rendering
  - export actions

## Data Model

### `projects`

Stores uploaded CSV metadata.

### `runs`

Stores profiling execution lifecycle.

### `profiling_results`

Stores final profiling output:

- `numeric_stats`
- `categorical_stats`
- `date_stats`
- `correlation_stats`
- `pps_stats`

## Run Flow

1. User uploads CSV through `POST /projects`
2. User starts profiling with `POST /projects/{project_id}/run`
3. Backend creates a `runs` row with status `queued`
4. Celery worker picks up the run
5. Worker computes profiling stats step by step
6. Worker updates run status in PostgreSQL
7. Worker publishes Redis Pub/Sub events on `run_progress:{run_id}`
8. FastAPI exposes those updates via SSE at `GET /runs/{run_id}/events`
9. Frontend shows live progress
10. Final results are saved in `profiling_results`
11. Frontend fetches results from `GET /runs/{run_id}/metrics`
12. User can export JSON or CSV

## Progress Events

The worker currently publishes events such as:

- `run_started`
- `numeric_stats_started`
- `numeric_stats_completed`
- `categorical_stats_started`
- `categorical_stats_completed`
- `date_stats_started`
- `date_stats_completed`
- `correlation_stats_started`
- `correlation_stats_completed`
- `pps_stats_started`
- `pps_stats_completed`
- `run_completed`
- `run_failed`

## API Summary

### Projects

- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `DELETE /projects/{project_id}`
- `POST /projects/{project_id}/run`

### Runs

- `GET /runs/{run_id}/status`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/metrics`
- `GET /runs/{run_id}/export/json`
- `GET /runs/{run_id}/export/csv`

## Setup

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. PostgreSQL

Create a PostgreSQL database and update `backend/app/core/config.py` or `.env` with the correct connection string.

Example:

```env
DATABASE_URL=postgresql+psycopg://postgres:root@localhost:5432/async_csv_db
REDIS_URL=redis://localhost:6379/0
```

### 3. Redis

Run Redis locally:

```bash
redis-server
```

### 4. Start FastAPI

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### 5. Start Celery Worker

```bash
cd backend
source .venv/bin/activate
celery -A app.workers.celery_app.celery_app worker --loglevel=info
```

### 6. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

- `http://localhost:3000`

Backend docs:

- `http://localhost:8000/docs`

## Testing the Flow

1. Open the workspace
2. Create a project with a CSV file
3. Open the project detail page
4. Click `Next Step`
5. Watch live progress update
6. Review metrics tables and heatmaps
7. Download JSON or CSV exports

## Assumptions

- Input format is currently CSV only
- One project corresponds to one uploaded CSV file
- One run processes one project file
- Local file storage is used for uploaded files
- Redis is available locally

## Tradeoffs

- CSV-only input keeps the async architecture simple and clear
- SSE was chosen instead of WebSocket because updates are one-way from server to UI
- Profiling logic is implemented with pandas for simplicity and maintainability
- Export is currently based on run results directly

## Limitations

- Review/edit/finalize workflow is not yet implemented
- Retry failed runs is not yet implemented
- Authentication is not implemented
- File storage is local, not abstracted to S3 or cloud storage
- Tests are not yet added
- Docker Compose is present but may need alignment with the latest local runtime setup

## Sample Output

The profiling result currently includes:

- numeric stats table
- categorical stats table
- date stats table
- correlation matrix
- PPS matrix

## AI Usage

AI tools were used during development for planning, implementation assistance, and iterative refinement.
