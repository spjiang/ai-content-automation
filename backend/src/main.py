from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.routers import health, jobs, metrics, packages, review, topics
from src.infrastructure.observability.logging_config import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging("api")
    yield


app = FastAPI(
    title="AI Content Automation API",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")
app.include_router(packages.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")
app.include_router(topics.router, prefix="/api/v1")
