from typing import Dict, List, Optional
from faults.base import BaseFault


class FaultRegistry:
    """Registry maintaining all available and active fault scenarios."""

    def __init__(self):
        self._faults: Dict[str, BaseFault] = {}

    def register(self, fault: BaseFault) -> None:
        self._faults[fault.id] = fault

    def get(self, fault_id: str) -> Optional[BaseFault]:
        return self._faults.get(fault_id)

    def list_all(self) -> List[dict]:
        return [f.get_info() for f in self._faults.values()]

    def list_active(self) -> List[dict]:
        return [f.get_info() for f in self._faults.values() if f.is_active()]


registry = FaultRegistry()
