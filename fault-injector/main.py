from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from config import settings
from faults import registry
from telemetry import ACTIVE_FAULTS_TOTAL, FAULT_STATE_GAUGE, Telemetry

telemetry = Telemetry(
    service_name=settings.SERVICE_NAME,
    loki_url=settings.LOKI_URL,
    otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await telemetry.start()
    telemetry.logger.info("Fault Injector service initialized and ready.")
    yield
    # Cleanup any active faults on shutdown
    for fault_info in registry.list_active():
        f = registry.get(fault_info["id"])
        if f:
            try:
                await f.deactivate()
            except Exception:
                pass


app = FastAPI(title="Sherlog Fault Injector", version="1.0.0", lifespan=lifespan)
telemetry.setup_middleware(app)


class ActivateRequest(BaseModel):
    params: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@app.get("/ready")
async def ready():
    return {
        "status": "ready",
        "service": settings.SERVICE_NAME,
        "total_faults_registered": len(registry.list_all()),
        "active_faults_count": len(registry.list_active()),
    }


@app.get("/faults")
async def list_faults():
    return registry.list_all()


@app.get("/faults/active")
async def list_active_faults():
    return registry.list_active()


@app.post("/faults/{fault_id}/activate")
async def activate_fault(fault_id: str, req: Optional[ActivateRequest] = None):
    fault = registry.get(fault_id)
    if not fault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fault '{fault_id}' not found in registry",
        )

    telemetry.logger.warning(
        f"Injecting fault '{fault_id}' targeting {fault.target_service}"
    )

    try:
        params = req.params if req else None
        res = await fault.activate(params=params)
        FAULT_STATE_GAUGE.labels(
            fault_id=fault.id, target_service=fault.target_service
        ).set(1.0)
        ACTIVE_FAULTS_TOTAL.labels(service=settings.SERVICE_NAME).set(
            len(registry.list_active())
        )
        return res
    except Exception as exc:
        telemetry.logger.error(
            f"Failed to activate fault '{fault_id}': {exc}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate fault: {exc}",
        )


@app.post("/faults/{fault_id}/deactivate")
async def deactivate_fault(fault_id: str):
    fault = registry.get(fault_id)
    if not fault:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fault '{fault_id}' not found in registry",
        )

    telemetry.logger.info(
        f"Deactivating fault '{fault_id}' targeting {fault.target_service}"
    )

    try:
        res = await fault.deactivate()
        FAULT_STATE_GAUGE.labels(
            fault_id=fault.id, target_service=fault.target_service
        ).set(0.0)
        ACTIVE_FAULTS_TOTAL.labels(service=settings.SERVICE_NAME).set(
            len(registry.list_active())
        )
        return res
    except Exception as exc:
        telemetry.logger.error(
            f"Failed to deactivate fault '{fault_id}': {exc}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate fault: {exc}",
        )


@app.post("/faults/reset")
async def reset_all_faults():
    telemetry.logger.info("Resetting all active faults to inactive baseline")
    results = []
    for fault_info in registry.list_active():
        fault = registry.get(fault_info["id"])
        if fault:
            try:
                res = await fault.deactivate()
                FAULT_STATE_GAUGE.labels(
                    fault_id=fault.id, target_service=fault.target_service
                ).set(0.0)
                results.append(res)
            except Exception as e:
                results.append({"fault_id": fault.id, "error": str(e)})

    ACTIVE_FAULTS_TOTAL.labels(service=settings.SERVICE_NAME).set(0.0)
    return {"status": "all_faults_reset", "deactivated": results}
