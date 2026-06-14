import asyncio
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.backend.pipeline.orchestrator import run_pipeline_async

logger = logging.getLogger(__name__)

router = APIRouter()


class ResearchRequest(BaseModel):
    """Request to start a research analysis."""

    competitors: list[str] = Field(
        ..., description="List of competitor names", min_items=1, max_items=10
    )
    topics: list[str] = Field(
        ..., description="List of topics to research", min_items=1, max_items=10
    )
    urls: list[str] = Field(
        ..., description="Source URLs to analyze", min_items=1, max_items=5
    )
    llm_provider: str = Field(
        default="google",
        description="LLM provider to use (google, anthropic, openai)",
    )


@router.post("/run", response_class=EventSourceResponse)
async def run_research(
    competitors: str = Query(..., description="JSON string of competitors list"),
    topics: str = Query(..., description="JSON string of topics list"),
    urls: str = Query(..., description="JSON string of urls list"),
    llm_provider: str = Query(default="google", description="LLM provider"),
) -> EventSourceResponse:
    """Start market research analysis with SSE progress streaming.

    Streams progress events as the pipeline runs:
    - scraping: fetching URLs
    - summarizing: generating summary
    - judging: checking for hallucinations
    - done: complete result
    - error: failure with message

    Note: Uses query params instead of JSON body because EventSource/SSE
    can only be used with GET requests. Frontend sends as query params.

    Args:
        competitors: JSON string of competitor list
        topics: JSON string of topics list
        urls: JSON string of urls list
        llm_provider: LLM provider (google, anthropic, openai)

    Returns:
        EventSourceResponse streaming progress events + final result

    Example client (JavaScript):
        const params = new URLSearchParams({
            competitors: JSON.stringify(['OpenAI', 'Mistral']),
            topics: JSON.stringify(['Pricing']),
            urls: JSON.stringify(['https://...']),
            llm_provider: 'google'
        });
        const eventSource = new EventSource(`/api/research/run?${params}`);
        eventSource.addEventListener('message', (e) => {
            const event = JSON.parse(e.data);
            console.log(event.stage, event.message);
            if (event.stage === 'done') {
                const result = event.result;
                eventSource.close();
            }
        });
    """

    # Parse JSON query params
    try:
        competitors_list = json.loads(competitors)
        topics_list = json.loads(topics)
        urls_list = json.loads(urls)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in query params: {e}")
        error_event = {
            "stage": "error",
            "message": f"Invalid input: {str(e)}",
            "progress": 0,
        }
        async def error_gen():
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
        return EventSourceResponse(error_gen())

    async def event_generator():
        """Generate SSE events from pipeline."""
        try:
            logger.info(
                f"Starting research: {len(competitors_list)} competitors, "
                f"{len(urls_list)} URLs, provider={llm_provider}"
            )

            # Run pipeline with progress events
            async for event in run_pipeline_async(
                urls=urls_list,
                competitors=competitors_list,
                topics=topics_list,
                llm_provider=llm_provider,
            ):
                # Convert event to JSON
                event_json = json.dumps(event, default=str)

                # Send as SSE event
                if event["stage"] == "done":
                    yield f"event: result\ndata: {event_json}\n\n"
                    logger.info("Research complete")
                    break

                elif event["stage"] == "error":
                    yield f"event: error\ndata: {event_json}\n\n"
                    logger.error(f"Research failed: {event['message']}")
                    break

                else:
                    # Progress event
                    yield f"event: message\ndata: {event_json}\n\n"

        except Exception as e:
            logger.error(f"Error in event_generator: {e}")
            error_event = {
                "stage": "error",
                "message": f"Server error: {str(e)}",
                "progress": 0,
            }
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"

    return EventSourceResponse(event_generator())


@router.get("/history")
async def get_history(
    # user_id: int = Depends(get_current_user),  # Phase 4: auth
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    """Get user's past research runs.

    Returns list of previous runs in reverse chronological order.
    Phase 4 will add database persistence; for now, returns empty list.

    Args:
        limit: Maximum number of runs to return (default 50)

    Returns:
        Dict with 'runs' key containing list of past runs
    """
    logger.info(f"Fetching research history (limit={limit})")

    # TODO: Phase 4 - Query database for past runs
    # runs = repository.list_runs(user_id, limit=limit)
    # return {"runs": [r.to_dict() for r in runs]}

    # For now, return empty (Phase 4 adds DB)
    return {"runs": [], "message": "Database not yet implemented (Phase 4)"}


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    # user_id: int = Depends(get_current_user),  # Phase 4: auth
) -> dict:
    """Get a specific past research run by ID.

    Phase 4 will add database persistence; for now, returns error.

    Args:
        run_id: Run identifier

    Returns:
        Dict with run details (summary, verdicts, etc.)

    Raises:
        HTTPException 404: Run not found
    """
    logger.info(f"Fetching run {run_id}")

    # TODO: Phase 4 - Query database for run
    # run = repository.get_run(run_id, user_id)
    # if not run:
    #     raise HTTPException(status_code=404, detail="Run not found")
    # return run.to_dict()

    # For now, return 404
    raise HTTPException(status_code=404, detail="Database not yet implemented (Phase 4)")