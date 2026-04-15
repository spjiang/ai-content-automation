from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.routers import health

app = FastAPI(
    title="AI Content Automation API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
