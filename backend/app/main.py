"""FastAPI Hauptanwendung."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, documents, exports, insurances, invoices, products
from app.config import settings
from app.models.database import init_db
from app.scheduler.notification_job import start_scheduler, stop_scheduler

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s | %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starte Versicherungs-Backend")
    init_db()
    start_scheduler()
    yield
    stop_scheduler()
    log.info("Backend beendet")


app = FastAPI(title="Versicherungs-Assistent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insurances.router, prefix="/api/insurances", tags=["insurances"])
app.include_router(products.router, prefix="/api/products", tags=["products"])
app.include_router(invoices.router, prefix="/api/invoices", tags=["invoices"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(exports.router, prefix="/api/exports", tags=["exports"])


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
