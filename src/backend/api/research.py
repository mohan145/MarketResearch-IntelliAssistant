import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from src.backend.api.auth import get_current_user
from src.backend.database import get_session
from src.backend.models import ResearchRun, User
from src.backend.pipeline.orchestrator import run_pipeline_async

logger = logging.getLogger(__name__)

router = APIRouter()


def get_current_user_from_query(
    token: str = Query(default=None, description="JWT token (for SSE endpoints)"),
    db: Session = Depends(get_session),
) -> User:
    """Auth dependency for SSE endpoints where Authorization header can't be sent.

    EventSource API only supports GET and cannot set custom headers, so the JWT
    is passed as a ?token= query param instead (see ADR-004).
    """
    from fastapi import HTTPException, status
    from jose import JWTError, jwt
    from src.backend.config import get_settings

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        settings = get_settings()
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.api_route("/run", methods=["GET", "POST"], response_class=EventSourceResponse)
async def run_research(
    competitors: str = Query(..., description="JSON string of competitors list"),
    topics: str = Query(..., description="JSON string of topics list"),
    urls: str = Query(..., description="JSON string of urls list"),
    llm_provider: str = Query(default=None, description="LLM provider (uses .env if not specified)"),
    current_user: User = Depends(get_current_user_from_query),
    db: Session = Depends(get_session),
) -> EventSourceResponse:
    """Start market research analysis with SSE progress streaming.

    Streams progress events as the pipeline runs:
    - scraping: fetching URLs
    - summarizing: generating summary
    - judging: checking for hallucinations
    - done: complete result saved to DB
    - error: failure with message
    """
    from src.backend.config import get_settings
    settings = get_settings()
    if not llm_provider:
        llm_provider = settings.llm_provider

    try:
        competitors_list = json.loads(competitors)
        topics_list = json.loads(topics)
        urls_list = json.loads(urls)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in query params: {e}")
        async def error_gen():
            yield json.dumps({"stage": "error", "message": f"Invalid input: {str(e)}", "progress": 0})
        return EventSourceResponse(error_gen())

    async def event_generator():
        try:
            logger.info(
                f"Starting research for user={current_user.email}: "
                f"{len(competitors_list)} competitors, {len(urls_list)} URLs"
            )

            async for event in run_pipeline_async(
                urls=urls_list,
                competitors=competitors_list,
                topics=topics_list,
                llm_provider=llm_provider,
            ):
                def serialize_event(obj):
                    if isinstance(obj, BaseModel):
                        return obj.model_dump()
                    return str(obj)

                event_json = json.dumps(event, default=serialize_event)
                yield event_json

                if event["stage"] == "done":
                    # Save run to DB
                    pipeline_result = event["result"]
                    run = ResearchRun(
                        user_id=current_user.id,
                        topics=json.dumps(topics_list),
                        competitors=json.dumps(competitors_list),
                        urls=json.dumps(urls_list),
                        result_json=json.dumps(pipeline_result, default=serialize_event),
                        hallucination_count=pipeline_result.hallucination_count,
                        run_duration_seconds=pipeline_result.run_duration_seconds,
                    )
                    db.add(run)
                    db.commit()
                    logger.info(f"Run saved to DB: id={run.id}, user={current_user.email}")
                    return

                if event["stage"] == "error":
                    logger.info(f"Pipeline error, closing stream")
                    return

        except Exception as e:
            logger.error(f"Error in event_generator: {e}")
            yield json.dumps({"stage": "error", "message": f"Server error: {str(e)}", "progress": 0})

    return EventSourceResponse(event_generator())


@router.get("/history")
async def get_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    """Get the current user's past research runs, newest first."""
    runs = (
        db.query(ResearchRun)
        .filter(ResearchRun.user_id == current_user.id)
        .order_by(ResearchRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "runs": [
            {
                "id": r.id,
                "topics": json.loads(r.topics),
                "competitors": json.loads(r.competitors),
                "urls": json.loads(r.urls),
                "hallucination_count": r.hallucination_count,
                "run_duration_seconds": r.run_duration_seconds,
                "created_at": r.created_at.isoformat(),
                "result": json.loads(r.result_json),
            }
            for r in runs
        ]
    }


@router.get("/{run_id}")
async def get_run(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    """Get a specific past research run by ID, scoped to current user."""
    run = db.query(ResearchRun).filter(
        ResearchRun.id == run_id,
        ResearchRun.user_id == current_user.id,
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": run.id,
        "topics": json.loads(run.topics),
        "competitors": json.loads(run.competitors),
        "urls": json.loads(run.urls),
        "hallucination_count": run.hallucination_count,
        "run_duration_seconds": run.run_duration_seconds,
        "created_at": run.created_at.isoformat(),
        "result": json.loads(run.result_json),
    }