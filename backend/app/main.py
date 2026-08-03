import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401 — register models on Base.metadata
from app.api.v1 import (
    agenda,
    auth,
    calendars,
    events,
    faq,
    hosts,
    messages,
    notifications,
    orders,
    payments,
    questions,
    tickets,
    users,
)
from app.core.config import settings
from app.core.database import Base, engine

# Surface application INFO logs (email delivery, notification fan-out, …) on
# stdout. uvicorn only configures its own loggers, leaving the root at WARNING,
# so we attach a handler to the top-level "app" logger our modules log under.
_app_logger = logging.getLogger("app")
if not _app_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(levelname)s:     %(name)s - %(message)s")
    )
    _app_logger.addHandler(_handler)
_app_logger.setLevel(logging.INFO)
_app_logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP bootstrap: create tables on startup. Replace with Alembic
    # migrations once the schema stabilises.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Ren Event Ticketing Platform",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)

# CORS - allows the frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files (e.g. avatars) statically. The directory is created up
# front so the mount succeeds on a fresh checkout.
_uploads_dir = Path(settings.UPLOAD_DIR)
_uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_uploads_dir)), name="uploads")


@app.get("/")
async def root():
    return {"message": "Ren Event Ticketing System API is running! 🚀"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# API v1 routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(agenda.router, prefix=settings.API_V1_PREFIX)
app.include_router(calendars.router, prefix=settings.API_V1_PREFIX)
app.include_router(events.router, prefix=settings.API_V1_PREFIX)
app.include_router(faq.router, prefix=settings.API_V1_PREFIX)
app.include_router(hosts.router, prefix=settings.API_V1_PREFIX)
app.include_router(messages.router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications.router, prefix=settings.API_V1_PREFIX)
app.include_router(questions.router, prefix=settings.API_V1_PREFIX)
app.include_router(tickets.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(orders.router, prefix=settings.API_V1_PREFIX)
app.include_router(payments.router, prefix=settings.API_V1_PREFIX)
