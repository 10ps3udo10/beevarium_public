from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user


router = APIRouter(prefix="/events", tags=["events"])


@router.get("/api", response_model=list[schemas.ApiEventResponse])
def list_api_events(
    limit: int = 25,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 100))
    return (
        db.query(models.ApiEvent)
        .filter(models.ApiEvent.user_id == current_user.id)
        .order_by(models.ApiEvent.created_at.desc())
        .limit(safe_limit)
        .all()
    )


@router.get("/summary", response_model=schemas.ApiObservabilitySummary)
def api_observability_summary(
    limit: int = 500,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 1000))
    events = (
        db.query(models.ApiEvent)
        .filter(models.ApiEvent.user_id == current_user.id)
        .order_by(models.ApiEvent.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    requests = len(events)
    errors = sum(1 for event in events if event.status_code >= 400)
    durations = sorted(float(event.duration_ms) for event in events)
    p95_index = max(0, int((len(durations) - 1) * 0.95)) if durations else 0
    grouped: dict[str, list[models.ApiEvent]] = {}
    for event in events:
        if event.path.startswith(("/visites", "/ruchers", "/ruches", "/ia-vocale")):
            grouped.setdefault(event.path, []).append(event)
    critical_paths = [
        schemas.ApiObservabilityPath(
            path=path,
            requests=len(path_events),
            errors=sum(1 for event in path_events if event.status_code >= 400),
            average_duration_ms=round(sum(float(event.duration_ms) for event in path_events) / len(path_events), 2),
        )
        for path, path_events in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True)[:5]
    ]
    return schemas.ApiObservabilitySummary(
        window_events=requests,
        requests=requests,
        errors=errors,
        error_rate_percent=round((errors / requests) * 100, 2) if requests else 0,
        average_duration_ms=round(sum(durations) / requests, 2) if requests else 0,
        p95_duration_ms=durations[p95_index] if durations else 0,
        critical_paths=critical_paths,
    )