from datetime import datetime, timezone
from uuid import uuid4

from app.db.session import SessionLocal
from app.models.profiling_result import ProfilingResult
from app.models.project import Project
from app.models.run import Run
from app.services.profiling_service import ProfilingService
from app.workers.celery_app import celery_app
from app.workers.progress import publish_run_event


def _update_run(
    run: Run,
    *,
    status: str,
    progress: int,
    current_stage: str,
    error_message: str | None = None,
) -> None:
    run.status = status
    run.progress = progress
    run.current_stage = current_stage
    run.error_message = error_message


def _set_run_state(
    run: Run,
    *,
    status: str,
    progress: int,
    current_stage: str,
    message: str,
    error_message: str | None = None,
) -> None:
    _update_run(
        run,
        status=status,
        progress=progress,
        current_stage=current_stage,
        error_message=error_message,
    )
    publish_run_event(
        run_id=str(run.id),
        project_id=str(run.project_id),
        status=status,
        progress=progress,
        current_stage=current_stage,
        message=message,
    )


@celery_app.task(name="app.workers.tasks.process_run")
def process_run(run_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if not run:
            return

        project = db.get(Project, run.project_id)
        if not project:
            _set_run_state(
                run,
                status="failed",
                progress=0,
                current_stage="project_lookup_failed",
                message="Project lookup failed",
                error_message="Project not found for run",
            )
            db.commit()
            return

        run.started_at = datetime.now(timezone.utc)
        _set_run_state(
            run,
            status="processing",
            progress=5,
            current_stage="run_started",
            message="Profiling run started",
        )
        db.commit()

        profiling_service = ProfilingService()
        dataframe, numeric_columns, categorical_columns, date_columns = profiling_service.prepare_dataframe(
            project.stored_path
        )

        _set_run_state(
            run,
            status="processing",
            progress=10,
            current_stage="numeric_stats_started",
            message="Numeric profiling started",
        )
        db.commit()
        numeric_stats = profiling_service.compute_numeric_stats(dataframe, numeric_columns)

        _set_run_state(
            run,
            status="processing",
            progress=25,
            current_stage="numeric_stats_completed",
            message="Numeric profiling completed",
        )
        db.commit()

        _set_run_state(
            run,
            status="processing",
            progress=35,
            current_stage="categorical_stats_started",
            message="Categorical profiling started",
        )
        db.commit()
        categorical_stats = profiling_service.compute_categorical_stats(dataframe, categorical_columns)

        _set_run_state(
            run,
            status="processing",
            progress=50,
            current_stage="categorical_stats_completed",
            message="Categorical profiling completed",
        )
        db.commit()

        _set_run_state(
            run,
            status="processing",
            progress=60,
            current_stage="date_stats_started",
            message="Date profiling started",
        )
        db.commit()
        date_stats = profiling_service.compute_date_stats(dataframe, date_columns)

        _set_run_state(
            run,
            status="processing",
            progress=70,
            current_stage="date_stats_completed",
            message="Date profiling completed",
        )
        db.commit()

        _set_run_state(
            run,
            status="processing",
            progress=78,
            current_stage="correlation_stats_started",
            message="Correlation analysis started",
        )
        db.commit()
        correlation_stats = profiling_service.compute_correlation_stats(dataframe, numeric_columns)

        _set_run_state(
            run,
            status="processing",
            progress=86,
            current_stage="correlation_stats_completed",
            message="Correlation analysis completed",
        )
        db.commit()

        _set_run_state(
            run,
            status="processing",
            progress=90,
            current_stage="pps_stats_started",
            message="PPS analysis started",
        )
        db.commit()
        pps_stats = profiling_service.compute_pps_stats(
            dataframe,
            numeric_columns,
            categorical_columns,
        )

        _set_run_state(
            run,
            status="processing",
            progress=95,
            current_stage="pps_stats_completed",
            message="PPS analysis completed",
        )
        db.commit()

        profiling_result = ProfilingResult(
            id=uuid4(),
            run_id=run.id,
            numeric_stats=numeric_stats,
            categorical_stats=categorical_stats,
            date_stats=date_stats,
            correlation_stats=correlation_stats,
            pps_stats=pps_stats,
        )
        db.add(profiling_result)

        run.completed_at = datetime.now(timezone.utc)
        _set_run_state(
            run,
            status="completed",
            progress=100,
            current_stage="run_completed",
            message="Profiling result stored and run completed",
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(Run, run_id)
        if run:
            _set_run_state(
                run,
                status="failed",
                progress=100,
                current_stage="run_failed",
                message="Profiling run failed",
                error_message=str(exc),
            )
            db.commit()
        raise
    finally:
        db.close()
