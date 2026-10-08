from contextlib import asynccontextmanager
from typing import List

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, status

from config import settings
from models import (
    AlertmanagerWebhookPayload,
    CheckoutRequest,
    CheckoutResponse,
)
from telemetry import INCOMING_ALERTS_TOTAL, Telemetry

telemetry = Telemetry(
    service_name=settings.SERVICE_NAME,
    loki_url=settings.LOKI_URL,
    otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telemetry.start()
    telemetry.logger.info("API Gateway initialized and ready.")
    yield


app = FastAPI(title="Sherlog API Gateway", version="1.0.0", lifespan=lifespan)
telemetry.setup_middleware(app)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.get("/ready")
async def ready():
    # Ping downstream orders service
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.ORDERS_SERVICE_URL}/health")
            if resp.status_code == 200:
                return {
                    "status": "ready",
                    "service": settings.SERVICE_NAME,
                    "orders_service": "healthy",
                }
    except Exception:
        pass
    return {
        "status": "ready",
        "service": settings.SERVICE_NAME,
        "orders_service": "degraded",
    }


@app.post("/api/v1/checkout", response_model=CheckoutResponse)
async def checkout(req: CheckoutRequest):
    telemetry.logger.info(
        f"Checkout initiated: customer='{req.customer_id}', {len(req.items)} items, currency={req.currency}"
    )

    headers = telemetry.get_propagation_headers()
    async with httpx.AsyncClient(timeout=settings.ORDERS_TIMEOUT_SEC) as client:
        try:
            resp = await client.post(
                f"{settings.ORDERS_SERVICE_URL}/orders",
                json={
                    "customer_id": req.customer_id,
                    "currency": req.currency,
                    "items": [it.model_dump() for it in req.items],
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            telemetry.logger.info(
                f"Checkout successful: Order #{data['id']} marked as {data['status']}"
            )
            return CheckoutResponse(
                order_id=data["id"],
                customer_id=data["customer_id"],
                total_amount=data["total_amount"],
                currency=data["currency"],
                status=data["status"],
                items=data.get("items", []),
                message="Order placed and processed successfully",
            )
        except httpx.TimeoutException as exc:
            telemetry.logger.error(
                f"Timeout forwarding checkout to Orders service ({settings.ORDERS_TIMEOUT_SEC}s): {exc}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Orders service timed out after {settings.ORDERS_TIMEOUT_SEC}s",
            )
        except httpx.HTTPStatusError as exc:
            telemetry.logger.error(
                f"Orders service returned HTTP {exc.response.status_code}: {exc.response.text}"
            )
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=exc.response.text,
            )
        except httpx.RequestError as exc:
            telemetry.logger.error(
                f"Failed to communicate with Orders service at {settings.ORDERS_SERVICE_URL}: {exc}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Orders service unreachable: {exc}",
            )


@app.get("/api/v1/orders")
async def list_orders(limit: int = 10):
    headers = telemetry.get_propagation_headers()
    async with httpx.AsyncClient(timeout=settings.ORDERS_TIMEOUT_SEC) as client:
        try:
            resp = await client.get(
                f"{settings.ORDERS_SERVICE_URL}/orders?limit={limit}",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@app.get("/api/v1/orders/{order_id}")
async def get_order(order_id: int):
    headers = telemetry.get_propagation_headers()
    async with httpx.AsyncClient(timeout=settings.ORDERS_TIMEOUT_SEC) as client:
        try:
            resp = await client.get(
                f"{settings.ORDERS_SERVICE_URL}/orders/{order_id}",
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@app.post("/api/v1/webhooks/alertmanager")
async def alertmanager_webhook(
    payload: AlertmanagerWebhookPayload,
    authorization: str = Header(default=""),
):
    # Verify shared secret
    expected_token = f"Bearer {settings.WEBHOOK_SECRET}"
    if authorization != expected_token and settings.WEBHOOK_SECRET:
        telemetry.logger.warning(
            "Unauthorized Alertmanager webhook attempt: invalid token"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook shared secret token",
        )

    telemetry.logger.info(
        f"Alertmanager webhook received: status='{payload.status}', {len(payload.alerts)} alerts"
    )

    for alert in payload.alerts:
        alertname = alert.labels.get("alertname", "UnknownAlert")
        severity = alert.labels.get("severity", "warning")
        INCOMING_ALERTS_TOTAL.labels(
            service=settings.SERVICE_NAME,
            alertname=alertname,
            severity=severity,
        ).inc()

        telemetry.logger.warning(
            f"Alert dispatched: alertname='{alertname}' severity='{severity}' summary='{alert.annotations.get('summary', '')}'"
        )

    return {"status": "accepted", "received_alerts": len(payload.alerts)}
