from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from anpr.services.channel_service import ChannelService

router = APIRouter()
_SERVICE: Optional[ChannelService] = None


class CreateChannelRequest(BaseModel):
    name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    roi: dict = Field(default_factory=dict)


class UpdateROIRequest(BaseModel):
    roi: dict


def set_channel_service(service: ChannelService) -> None:
    global _SERVICE
    _SERVICE = service


def _svc() -> ChannelService:
    if _SERVICE is None:
        raise RuntimeError("Channel service is not initialized")
    return _SERVICE


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/channels")
def list_channels() -> list[dict]:
    return [channel.__dict__ for channel in _svc().list_channels()]


@router.post("/channels")
def create_channel(payload: CreateChannelRequest) -> dict:
    channel = _svc().add_channel(payload.name, payload.source, payload.roi)
    return channel.__dict__


@router.delete("/channels/{channel_id}")
def delete_channel(channel_id: int) -> dict:
    if not _svc().remove_channel(channel_id):
        raise HTTPException(status_code=404, detail="Канал не найден")
    return {"ok": True}


@router.patch("/channels/{channel_id}/roi")
def update_roi(channel_id: int, payload: UpdateROIRequest) -> dict:
    if not _svc().update_roi(channel_id, payload.roi):
        raise HTTPException(status_code=404, detail="Канал не найден")
    return {"ok": True}


@router.get("/channels/{channel_id}/snapshot")
def snapshot(channel_id: int) -> Response:
    frame = _svc().get_frame(channel_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="Снимок недоступен")
    return Response(content=frame, media_type="image/jpeg")


@router.get("/telemetry")
def telemetry() -> dict:
    return {"channels": _svc().telemetry.snapshot()}


@router.get("/events/stream")
async def stream_events() -> StreamingResponse:
    async def event_generator():
        while True:
            events = _svc().telemetry.pop_events()
            if events:
                payload = json.dumps(events, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/video-gateway/profiles")
def profiles() -> dict:
    return {
        "profiles": ["high", "medium", "low"],
        "transport": {"live": "WebRTC", "archive": "HLS", "ingest": "RTSP"},
    }
