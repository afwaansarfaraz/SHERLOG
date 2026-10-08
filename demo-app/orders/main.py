import asyncio
import time
from contextlib import asynccontextmanager
from typing import List

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from database import check_db_health, engine, get_db
from models import OrderCreate, OrderItemModel, OrderModel, OrderResponse
from telemetry import (
    DB_CONNECTIONS_ACTIVE,
    DB_POOL_EXHAUSTION_ERRORS,
    DEPENDENCY_TIMEOUTS_TOTAL,
    INJECTED_FAULT_ACTIVE,
    SLOW_QUERIES_TOTAL,
    Telemetry,
)

telemetry = Telemetry(
    service_name=settings.SERVICE_NAME,
    loki_url=settings.LOKI_URL,
    otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
)

# Pool exhaustion connection holders
held_connections: list = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telemetry.start()
    telemetry.logger.info("Orders service initialized and ready.")
    yield
    # Cleanup held connections if any on shutdown
    for conn in held_connections:
        try:
            conn.close()
        except Exception:
            pass


app = FastAPI(title="Sherlog Orders Service", version="1.0.0", lifespan=lifespan)
telemetry.setup_middleware(app)


class FaultToggleRequest(BaseModel):
    active: bool
    delay_sec: float = 1.8


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.get("/ready")
async def ready():
    db_ok = check_db_health()
    if not db_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )
    return {"status": "ready", "service": settings.SERVICE_NAME, "db": "connected"}


@app.get("/internal/faults/status")
async def fault_status():
    return {
        "pool_exhaustion_active": settings.INJECTED_POOL_EXHAUSTION_ACTIVE,
        "held_connections": len(held_connections),
        "slow_query_active": settings.INJECTED_SLOW_QUERY_ACTIVE,
        "slow_query_delay_sec": settings.INJECTED_SLOW_QUERY_DELAY_SEC,
        "config_error_active": settings.INJECTED_CONFIG_ERROR_ACTIVE,
    }


@app.post("/internal/faults/db-pool-exhaustion")
async def toggle_db_pool_exhaustion(req: FaultToggleRequest):
    global held_connections
    settings.INJECTED_POOL_EXHAUSTION_ACTIVE = req.active
    INJECTED_FAULT_ACTIVE.labels(
        service=settings.SERVICE_NAME, fault_id="db_pool_exhaustion"
    ).set(1.0 if req.active else 0.0)

    if req.active:
        telemetry.logger.warning(
            "Fault active: db_pool_exhaustion. Checking out all pool connections."
        )
        # Check out connections up to pool_size + max_overflow
        target_conns = settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW
        while len(held_connections) < target_conns:
            try:
                conn = engine.connect()
                # Keep connection alive with active query
                conn.execute(text("SELECT 1"))
                held_connections.append(conn)
            except Exception as e:
                telemetry.logger.error(f"Error checking out connection: {e}")
                break
        DB_CONNECTIONS_ACTIVE.labels(service=settings.SERVICE_NAME).set(
            engine.pool.checkedout()
        )
    else:
        telemetry.logger.info("Deactivating db_pool_exhaustion fault. Releasing connections.")
        for conn in held_connections:
            try:
                conn.close()
            except Exception:
                pass
        held_connections.clear()
        DB_CONNECTIONS_ACTIVE.labels(service=settings.SERVICE_NAME).set(
            engine.pool.checkedout()
        )

    return {
        "status": "updated",
        "fault": "db_pool_exhaustion",
        "active": req.active,
        "held_connections": len(held_connections),
    }


@app.post("/internal/faults/slow-query")
async def toggle_slow_query(req: FaultToggleRequest):
    settings.INJECTED_SLOW_QUERY_ACTIVE = req.active
    settings.INJECTED_SLOW_QUERY_DELAY_SEC = req.delay_sec
    INJECTED_FAULT_ACTIVE.labels(
        service=settings.SERVICE_NAME, fault_id="slow_query"
    ).set(1.0 if req.active else 0.0)
    telemetry.logger.warning(
        f"Fault slow_query updated: active={req.active}, delay={req.delay_sec}s"
    )
    return {
        "status": "updated",
        "fault": "slow_query",
        "active": req.active,
        "delay_sec": req.delay_sec,
    }


@app.post("/internal/faults/config-error")
async def toggle_config_error(req: FaultToggleRequest):
    settings.INJECTED_CONFIG_ERROR_ACTIVE = req.active
    INJECTED_FAULT_ACTIVE.labels(
        service=settings.SERVICE_NAME, fault_id="configuration_error"
    ).set(1.0 if req.active else 0.0)
    telemetry.logger.warning(
        f"Fault configuration_error updated: active={req.active}"
    )
    return {
        "status": "updated",
        "fault": "configuration_error",
        "active": req.active,
    }


@app.post("/internal/faults/reset")
async def reset_faults():
    global held_connections
    settings.INJECTED_POOL_EXHAUSTION_ACTIVE = False
    settings.INJECTED_SLOW_QUERY_ACTIVE = False
    settings.INJECTED_CONFIG_ERROR_ACTIVE = False

    INJECTED_FAULT_ACTIVE.labels(service=settings.SERVICE_NAME, fault_id="db_pool_exhaustion").set(0.0)
    INJECTED_FAULT_ACTIVE.labels(service=settings.SERVICE_NAME, fault_id="slow_query").set(0.0)
    INJECTED_FAULT_ACTIVE.labels(service=settings.SERVICE_NAME, fault_id="configuration_error").set(0.0)

    for conn in held_connections:
        try:
            conn.close()
        except Exception:
            pass
    held_connections.clear()
    DB_CONNECTIONS_ACTIVE.labels(service=settings.SERVICE_NAME).set(engine.pool.checkedout())
    telemetry.logger.info("Orders faults reset to default.")
    return {"status": "reset"}


@app.post("/orders", response_model=OrderResponse)
async def create_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    telemetry.logger.info(
        f"Initiating order creation for customer '{order_in.customer_id}' with {len(order_in.items)} items"
    )

    total_amount = sum(item.price * item.quantity for item in order_in.items)

    # 1. Simulate DB pool exhaustion check
    try:
        order = OrderModel(
            customer_id=order_in.customer_id,
            total_amount=total_amount,
            currency=order_in.currency,
            status="PENDING",
        )
        db.add(order)
        db.flush()

        for item_in in order_in.items:
            db_item = OrderItemModel(
                order_id=order.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                price=item_in.price,
            )
            db.add(db_item)
        db.commit()
        db.refresh(order)
    except Exception as exc:
        db.rollback()
        if "timeout" in str(exc).lower() or "queuepool" in str(exc).lower():
            DB_POOL_EXHAUSTION_ERRORS.labels(service=settings.SERVICE_NAME).inc()
            telemetry.logger.critical(
                f"DB Pool Exhaustion on create_order: QueuePool timed out after {settings.DB_POOL_TIMEOUT}s. Active connections: {engine.pool.checkedout()}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection pool exhausted: timeout waiting for connection ({settings.DB_POOL_TIMEOUT}s)",
            )
        raise

    # 2. Call Payments service
    payments_url = settings.PAYMENTS_SERVICE_URL
    if settings.INJECTED_CONFIG_ERROR_ACTIVE:
        payments_url = "http://invalid-payments-upstream.internal:9999"
        telemetry.logger.error(
            f"ConfigurationError: misconfigured payment gateway endpoint: {payments_url}"
        )

    headers = telemetry.get_propagation_headers()
    async with httpx.AsyncClient(timeout=settings.PAYMENTS_TIMEOUT_SEC) as client:
        try:
            telemetry.logger.info(
                f"Calling Payments service at {payments_url}/payments/process for Order #{order.id}"
            )
            pay_resp = await client.post(
                f"{payments_url}/payments/process",
                json={
                    "order_id": order.id,
                    "amount": float(order.total_amount),
                    "currency": order.currency,
                    "customer_id": order.customer_id,
                },
                headers=headers,
            )
            pay_resp.raise_for_status()
            order.status = "COMPLETED"
            db.commit()
            db.refresh(order)
            telemetry.logger.info(
                f"Order #{order.id} confirmed and marked COMPLETED"
            )
        except httpx.TimeoutException as exc:
            DEPENDENCY_TIMEOUTS_TOTAL.labels(
                service=settings.SERVICE_NAME, dependency="payments"
            ).inc()
            order.status = "PAYMENT_TIMEOUT"
            db.commit()
            telemetry.logger.error(
                f"Downstream dependency timeout calling Payments service for Order #{order.id}: {exc}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Payment service timed out after {settings.PAYMENTS_TIMEOUT_SEC}s",
            )
        except (httpx.ConnectError, httpx.RequestError) as exc:
            order.status = "PAYMENT_FAILED"
            db.commit()
            telemetry.logger.error(
                f"Downstream connection error calling Payments at {payments_url}: {exc}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to communicate with payment gateway: {exc}",
            )
        except httpx.HTTPStatusError as exc:
            order.status = "PAYMENT_DECLINED"
            db.commit()
            telemetry.logger.warning(
                f"Payments returned HTTP {exc.response.status_code} for Order #{order.id}"
            )
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"Payment declined: {exc.response.text}",
            )

    return OrderResponse(
        id=order.id,
        customer_id=order.customer_id,
        total_amount=float(order.total_amount),
        currency=order.currency,
        status=order.status,
        items=[
            {
                "id": it.id,
                "product_id": it.product_id,
                "quantity": it.quantity,
                "price": float(it.price),
            }
            for it in order.items
        ],
        created_at=order.created_at,
    )


@app.get("/orders", response_model=List[OrderResponse])
async def list_orders(limit: int = 10, db: Session = Depends(get_db)):
    telemetry.logger.info(f"Fetching orders list (limit={limit})")

    # If slow query fault is active, simulate expensive DB operation
    if settings.INJECTED_SLOW_QUERY_ACTIVE:
        telemetry.logger.warning(
            f"Slow query fault active: executing heavy DB query with delay={settings.INJECTED_SLOW_QUERY_DELAY_SEC}s"
        )
        SLOW_QUERIES_TOTAL.labels(service=settings.SERVICE_NAME).inc()
        try:
            db.execute(text(f"SELECT pg_sleep({settings.INJECTED_SLOW_QUERY_DELAY_SEC})"))
        except Exception:
            # Fallback sleep if pg_sleep unavailable
            await asyncio.sleep(settings.INJECTED_SLOW_QUERY_DELAY_SEC)

    try:
        orders = db.query(OrderModel).order_by(OrderModel.id.desc()).limit(limit).all()
        return [
            OrderResponse(
                id=o.id,
                customer_id=o.customer_id,
                total_amount=float(o.total_amount),
                currency=o.currency,
                status=o.status,
                items=[
                    {
                        "id": it.id,
                        "product_id": it.product_id,
                        "quantity": it.quantity,
                        "price": float(it.price),
                    }
                    for it in o.items
                ],
                created_at=o.created_at,
            )
            for o in orders
        ]
    except Exception as exc:
        if "timeout" in str(exc).lower() or "queuepool" in str(exc).lower():
            DB_POOL_EXHAUSTION_ERRORS.labels(service=settings.SERVICE_NAME).inc()
            telemetry.logger.critical(
                f"DB Pool Exhaustion on list_orders: {exc}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection pool exhausted: timeout waiting for connection ({settings.DB_POOL_TIMEOUT}s)",
            )
        raise


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    try:
        order = db.query(OrderModel).filter(OrderModel.id == order_id).first()
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )
        return OrderResponse(
            id=order.id,
            customer_id=order.customer_id,
            total_amount=float(order.total_amount),
            currency=order.currency,
            status=order.status,
            items=[
                {
                    "id": it.id,
                    "product_id": it.product_id,
                    "quantity": it.quantity,
                    "price": float(it.price),
                }
                for it in order.items
            ],
            created_at=order.created_at,
        )
    except Exception as exc:
        if "timeout" in str(exc).lower() or "queuepool" in str(exc).lower():
            DB_POOL_EXHAUSTION_ERRORS.labels(service=settings.SERVICE_NAME).inc()
            telemetry.logger.critical(
                f"DB Pool Exhaustion on get_order: {exc}", exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Database connection pool exhausted: timeout waiting for connection ({settings.DB_POOL_TIMEOUT}s)",
            )
        raise
