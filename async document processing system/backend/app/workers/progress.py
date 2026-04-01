import json
from datetime import datetime, timezone

from redis import Redis

from app.core.config import settings


redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def publish_run_event(
    *,
    run_id: str,
    project_id: str,
    status: str,
    progress: int,
    current_stage: str,
    message: str,
) -> None:
    payload = {
        "run_id": run_id,
        "project_id": project_id,
        "status": status,
        "progress": progress,
        "current_stage": current_stage,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.publish(f"run_progress:{run_id}", json.dumps(payload))
