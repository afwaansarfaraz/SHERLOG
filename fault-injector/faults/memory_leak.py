from typing import Any, Dict, Optional
from faults.base import BaseFault


class MemoryLeakFault(BaseFault):
    """Simulates progressive RSS memory consumption and heap exhaustion."""

    id = "memory_leak"
    name = "Simulated Memory Leak"
    description = "Simulates RSS memory consumption leak and heap exhaustion in microservices"
    target_service = "payments"
    category = "resource_exhaustion"

    def __init__(self):
        self._active = False
        self._leak_mb = 50

    def is_active(self) -> bool:
        return self._active

    async def activate(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if params and "leak_mb" in params:
            self._leak_mb = int(params["leak_mb"])
        self._active = True
        return {
            "fault_id": self.id,
            "status": "activated",
            "leak_mb": self._leak_mb,
        }

    async def deactivate(self) -> Dict[str, Any]:
        self._active = False
        return {"fault_id": self.id, "status": "deactivated"}
