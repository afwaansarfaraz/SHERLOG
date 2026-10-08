from typing import Any, Dict, Optional
import httpx
from config import settings
from faults.base import BaseFault


class DependencyTimeoutFault(BaseFault):
    id = "dependency_timeout"
    name = "Downstream Dependency Timeout"
    description = "Forces payments-service to delay responses beyond the orders-service HTTP client timeout ceiling"
    target_service = "payments"
    category = "dependency"

    def __init__(self):
        self._active = False

    def is_active(self) -> bool:
        return self._active

    async def activate(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        delay_sec = 8.0
        if params and "delay_sec" in params:
            delay_sec = float(params["delay_sec"])

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.PAYMENTS_SERVICE_URL}/internal/faults/dependency-timeout",
                json={"active": True, "delay_sec": delay_sec},
            )
            resp.raise_for_status()
            self._active = True
            return {
                "fault_id": self.id,
                "status": "activated",
                "delay_sec": delay_sec,
                "details": resp.json(),
            }

    async def deactivate(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.PAYMENTS_SERVICE_URL}/internal/faults/dependency-timeout",
                json={"active": False},
            )
            resp.raise_for_status()
            self._active = False
            return {
                "fault_id": self.id,
                "status": "deactivated",
                "details": resp.json(),
            }
