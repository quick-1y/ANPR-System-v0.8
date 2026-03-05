from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from anpr.web.routes import router, set_channel_service
from anpr.services.channel_service import ChannelService


app = FastAPI(title="ANPR Web Platform", version="0.8-web")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

service = ChannelService()
set_channel_service(service)
app.include_router(router, prefix="/api")
app.mount("/", StaticFiles(directory=str(Path("webui")), html=True), name="webui")


@app.on_event("shutdown")
def _shutdown() -> None:
    service.stop()


def run() -> None:
    uvicorn.run("anpr.web.main:app", host="0.0.0.0", port=8080, reload=False)
