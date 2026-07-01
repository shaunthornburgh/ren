from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Ren Event Ticketing Platform",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# CORS - allows the frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Ren Event Ticketing System API is running! 🚀"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


# API v1 routers are registered here as modules are implemented, e.g.:
# from app.api.v1 import auth
# app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
