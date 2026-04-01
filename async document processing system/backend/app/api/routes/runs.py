import csv
import io
import json
import time

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.profiling_result import ProfilingResult
from app.models.run import Run
from app.workers.progress import redis_client


router = APIRouter()


class RunStatusResponse(BaseModel):
    run_id: str
    project_id: str
    status: str
    progress: int
    current_stage: str
    error_message: str | None
    created_at: str
    started_at: str | None
    completed_at: str | None


class RunMetricsResponse(BaseModel):
    run_id: str
    numeric_stats: list | dict | None
    categorical_stats: list | dict | None
    date_stats: list | dict | None
    correlation_stats: list | dict | None
    pps_stats: list | dict | None


def _get_run_with_result(db: Session, run_id: str) -> tuple[Run, ProfilingResult]:
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    profiling_result = (
        db.query(ProfilingResult)
        .filter(ProfilingResult.run_id == run.id)
        .one_or_none()
    )
    if not profiling_result:
        raise HTTPException(status_code=404, detail="Profiling result not found for run")

    return run, profiling_result


@router.get("/{run_id}/status", response_model=RunStatusResponse)
def get_run_status(run_id: str, db: Session = Depends(get_db)) -> RunStatusResponse:
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunStatusResponse(
        run_id=str(run.id),
        project_id=str(run.project_id),
        status=run.status,
        progress=run.progress,
        current_stage=run.current_stage,
        error_message=run.error_message,
        created_at=run.created_at.isoformat(),
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
    )


@router.get("/{run_id}/events")
def stream_run_events(run_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    channel_name = f"run_progress:{run_id}"

    def event_stream():
        pubsub = redis_client.pubsub()
        pubsub.subscribe(channel_name)
        try:
            initial_payload = {
                "run_id": str(run.id),
                "project_id": str(run.project_id),
                "status": run.status,
                "progress": run.progress,
                "current_stage": run.current_stage,
                "message": "Subscribed to run progress stream",
                "timestamp": run.created_at.isoformat(),
            }
            yield f"data: {json.dumps(initial_payload)}\n\n"

            for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield f"data: {data}\n\n"

                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    payload = {}

                if payload.get("status") in {"completed", "failed"}:
                    break
        finally:
            pubsub.unsubscribe(channel_name)
            pubsub.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}/metrics", response_model=RunMetricsResponse)
def get_run_metrics(run_id: str, db: Session = Depends(get_db)) -> RunMetricsResponse:
    run, profiling_result = _get_run_with_result(db, run_id)

    return RunMetricsResponse(
        run_id=str(run.id),
        numeric_stats=profiling_result.numeric_stats,
        categorical_stats=profiling_result.categorical_stats,
        date_stats=profiling_result.date_stats,
        correlation_stats=profiling_result.correlation_stats,
        pps_stats=profiling_result.pps_stats,
    )


@router.get("/{run_id}/export/json")
def export_run_json(run_id: str, db: Session = Depends(get_db)) -> Response:
    run, profiling_result = _get_run_with_result(db, run_id)
    payload = {
        "run_id": str(run.id),
        "numeric_stats": profiling_result.numeric_stats,
        "categorical_stats": profiling_result.categorical_stats,
        "date_stats": profiling_result.date_stats,
        "correlation_stats": profiling_result.correlation_stats,
        "pps_stats": profiling_result.pps_stats,
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="run_{run_id}_metrics.json"'
        },
    )


@router.get("/{run_id}/export/csv")
def export_run_csv(run_id: str, db: Session = Depends(get_db)) -> Response:
    run, profiling_result = _get_run_with_result(db, run_id)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["section", "column_name", "metric", "value"])

    def write_stat_rows(section: str, stats: list | dict | None) -> None:
        if isinstance(stats, list):
            for row in stats:
                if not isinstance(row, dict):
                    continue
                column_name = row.get("column_name", "")
                for key, value in row.items():
                    if key == "column_name":
                        continue
                    writer.writerow([section, column_name, key, json.dumps(value)])
        elif isinstance(stats, dict):
            for outer_key, nested in stats.items():
                if isinstance(nested, dict):
                    for inner_key, value in nested.items():
                        writer.writerow([section, outer_key, inner_key, value])
                else:
                    writer.writerow([section, outer_key, "", nested])

    write_stat_rows("numeric_stats", profiling_result.numeric_stats)
    write_stat_rows("categorical_stats", profiling_result.categorical_stats)
    write_stat_rows("date_stats", profiling_result.date_stats)
    write_stat_rows("correlation_stats", profiling_result.correlation_stats)
    write_stat_rows("pps_stats", profiling_result.pps_stats)

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="run_{run_id}_metrics.csv"'
        },
    )
