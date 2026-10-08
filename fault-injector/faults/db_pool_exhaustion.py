from typing import Any, Dict, Optional
import httpx
from config import settings
from faults.base import BaseFault


class DbPoolExhaustionFault(BaseFault):
    id = "db_pool_exhaustion"
    name = "Database Connection Pool Exhaustion"
    description = "Exhausts the orders-service connection pool to cause query timeouts and checkout 503s"
    target_service = "orders"
    category = "resource_exhaustion"

    def __init__(self):
        self._active = False

    def is_active(self) -> bool:
        return self._active

    async def activate(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.ORDERS_SERVICE_URL}/internal/faults/db-pool-exhaustion",
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
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.ORDERS_SERVICE_URL}/internal/faults/db-pool-exhaustion",
                json={"active": False},
            )
            resp.raise_for_status()
            self._active = False
            return {
                "fault_id": self.id,
                "status": "deactivated",
                "details": resp.json(),
            }
