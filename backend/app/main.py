"""FastAPI application entry point.

Only the health endpoint is implemented so far. API modules under ``app/api/v1``
are structure stubs; see docs/api-contract.md for the planned contract.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import chat, data, health
from app.core.config import settings

app = FastAPI(
    title="Geospatial Climate Risk Intelligence API",
    version="0.1.0",
    description=(
        "Research prototype. Environmental observations are real; all companies, "
        "financial statements, bank exposures and insurance policies are synthetic."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(data.router, prefix=settings.api_prefix)
