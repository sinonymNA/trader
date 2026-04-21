from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.api import ControlResponse
from app.services.worker import WorkerState

router = APIRouter(prefix="/control", tags=["control"])


@router.post("/pause", response_model=ControlResponse)
async def pause(request: Request) -> ControlResponse:
    state: WorkerState = request.app.state.worker_state
    if state.killed:
        return ControlResponse(
            ok=False,
            worker_status=state.status,
            message="Worker is stopped and cannot be paused",
        )
    state.pause()
    return ControlResponse(
        ok=True,
        worker_status=state.status,
        message="Worker paused",
    )


@router.post("/resume", response_model=ControlResponse)
async def resume(request: Request) -> ControlResponse:
    state: WorkerState = request.app.state.worker_state
    if state.killed:
        return ControlResponse(
            ok=False,
            worker_status=state.status,
            message="Worker is stopped and cannot be resumed",
        )
    state.resume()
    return ControlResponse(
        ok=True,
        worker_status=state.status,
        message="Worker resumed",
    )
