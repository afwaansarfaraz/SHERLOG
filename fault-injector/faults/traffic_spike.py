import asyncio
import logging
from typing import Any, Dict, Optional
import httpx
from config import settings
from faults.base import BaseFault

logger = logging.getLogger("faults.traffic_spike")


class TrafficSpikeFault(BaseFault):
    id = "traffic_spike"
    name = "Sudden Traffic Spike"
    description = "Generates high concurrency load against the API gateway checkout endpoint"
    target_service = "api"
    category = "traffic"

    def __init__(self):
        self._active = False
        self._task: Optional[asyncio.Task] = None
        self._concurrency = 15
        self._rate_delay = 0.1

    def is_active(self) -> bool:
        return self._active

    async def _traffic_generator(self):
        sample_payload = {
            "customer_id": "cust_spike_user",
            "items": [
                {"product_id": "prod_spike_item", "quantity": 1, "price": 49.99}
            ],
            "currency": "USD",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            while self._active:
                tasks = []
                for _ in range(self._concurrency):
                    tasks.append(
                        client.post(
                            f"{settings.API_SERVICE_URL}/api/v1/checkout",
                            json=sample_payload,
                        )
                    )
                try:
                    await asyncio.gather(*tasks, return_exceptions=True)
                except Exception as exc:
                    logger.debug(f"Spike request exception: {exc}")
                await asyncio.sleep(self._rate_delay)

    async def activate(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._active:
            return {"fault_id": self.id, "status": "already_active"}

        if params:
            self._concurrency = int(params.get("concurrency", 15))
            self._rate_delay = float(params.get("rate_delay", 0.1))

        self._active = True
        self._task = asyncio.create_task(self._traffic_generator())
        return {
            "fault_id": self.id,
            "status": "activated",
            "concurrency": self._concurrency,
            "rate_delay": self._rate_delay,
        }

    async def deactivate(self) -> Dict[str, Any]:
        if not self._active:
            return {"fault_id": self.id, "status": "already_inactive"}

        self._active = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        return {"fault_id": self.id, "status": "deactivated"}
