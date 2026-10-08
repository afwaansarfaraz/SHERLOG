import asyncio
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from config import settings
from models import PaymentRequest, PaymentResponse
from telemetry import (
    INJECTED_FAULT_ACTIVE,
    Telemetry,
)

telemetry = Telemetry(
    service_name=settings.SERVICE_NAME,
    loki_url=settings.LOKI_URL,
    otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telemetry.start()
    telemetry.logger.info("Payments service initialized and ready.")
    yield


app = FastAPI(title="Sherlog Payments Service", version="1.0.0", lifespan=lifespan)
telemetry.setup_middleware(app)

# In-memory payments ledger
payments_db = {}


class FaultToggleRequest(BaseModel):
    active: bool
    delay_sec: float = 8.0


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.get("/ready")
async def ready():
    return {"status": "ready", "service": settings.SERVICE_NAME}


@app.get("/internal/faults/status")
async def get_fault_status():
    return {
        "dependency_timeout_active": settings.INJECTED_TIMEOUT_ACTIVE,
        "delay_sec": settings.INJECTED_TIMEOUT_DELAY_SEC,
    }


@app.post("/internal/faults/dependency-timeout")
async def toggle_dependency_timeout(req: FaultToggleRequest):
    settings.INJECTED_TIMEOUT_ACTIVE = req.active
    settings.INJECTED_TIMEOUT_DELAY_SEC = req.delay_sec
    INJECTED_FAULT_ACTIVE.labels(
        service=settings.SERVICE_NAME, fault_id="dependency_timeout"
    ).set(1.0 if req.active else 0.0)
    telemetry.logger.warning(
        f"Fault dependency_timeout updated: active={req.active}, delay={req.delay_sec}s"
    )
    return {
        "status": "updated",
        "fault": "dependency_timeout",
        "active": req.active,
        "delay_sec": req.delay_sec,
    }


@app.post("/internal/faults/reset")
async def reset_faults():
    settings.INJECTED_TIMEOUT_ACTIVE = False
    INJECTED_FAULT_ACTIVE.labels(
        service=settings.SERVICE_NAME, fault_id="dependency_timeout"
    ).set(0.0)
    telemetry.logger.info("Payments faults reset to default.")
    return {"status": "reset"}


@app.post("/payments/process", response_model=PaymentResponse)
async def process_payment(req: PaymentRequest):
    telemetry.logger.info(
        f"Processing payment request for Order #{req.order_id}, amount=${req.amount:.2f} {req.currency}"
    )

    # 1. Simulate fault condition if active
    if settings.INJECTED_TIMEOUT_ACTIVE:
        telemetry.logger.warning(
            f"Fault active: injecting {settings.INJECTED_TIMEOUT_DELAY_SEC}s delay on payment processing"
        )
        await asyncio.sleep(settings.INJECTED_TIMEOUT_DELAY_SEC)

    # 2. Simulate standard gateway processing delay
    if settings.BASE_LATENCY_MS > 0:
        await asyncio.sleep(settings.BASE_LATENCY_MS / 1000.0)

    # 3. Validation
    if req.amount > 10000.0:
        telemetry.logger.error(
            f"Payment declined for Order #{req.order_id}: amount ${req.amount} exceeds limit"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction amount exceeds allowed transaction ceiling",
        )

    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    tx_id = f"tx_{uuid.uuid4().hex[:16]}"
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    payment_record = PaymentResponse(
        payment_id=payment_id,
        order_id=req.order_id,
        amount=req.amount,
        currency=req.currency,
        status="CONFIRMED",
        transaction_id=tx_id,
        timestamp=timestamp,
    )
    payments_db[payment_id] = payment_record

    telemetry.logger.info(
        f"Payment confirmed: id={payment_id}, tx={tx_id}, order={req.order_id}"
    )
    return payment_record


@app.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str):
    if payment_id not in payments_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment record not found"
        )
    return payments_db[payment_id]
