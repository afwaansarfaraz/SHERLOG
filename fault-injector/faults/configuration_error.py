from typing import Any, Dict, Optional
import httpx
from config import settings
from faults.base import BaseFault


class ConfigurationErrorFault(BaseFault):
    id = "configuration_error"
    name = "Configuration Error"
    description = "Injects an invalid downstream service configuration leading to upstream resolution failures"
    target_service = "orders"
    category = "configuration"

    def __init__(self):
        self._active = False

    def is_active(self) -> bool:
        return self._active

    async def activate(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.ORDERS_SERVICE_URL}/internal/faults/config-error",
                json={"active": True},
            )
            resp.raise_for_status()
            self._active = True
            return {
                "fault_id": self.id,
                "status": "activated",
                "details": resp.json(),
            }

    async def deactivate(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.ORDERS_SERVICE_URL}/internal/faults/config-error",
                json={"active": False},
            )
            resp.raise_for_status()
            self._active = False
            return {
                "fault_id": self.id,
                "status": "deactivated",
                "details": resp.json(),
            }
