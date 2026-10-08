import sys
import os
import pytest

# Add fault-injector to python path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../fault-injector")))

from faults import registry
from faults.base import BaseFault


def test_registry_contains_initial_five_faults():
    faults = registry.list_all()
    fault_ids = {f["id"] for f in faults}
    
    expected = {
        "db_pool_exhaustion",
        "slow_query",
        "dependency_timeout",
        "traffic_spike",
        "configuration_error",
    }
    assert expected.issubset(fault_ids), f"Missing faults: {expected - fault_ids}"


def test_fault_metadata_structure():
    fault = registry.get("db_pool_exhaustion")
    assert fault is not None
    info = fault.get_info()
    
    assert info["id"] == "db_pool_exhaustion"
    assert info["target_service"] == "orders"
    assert info["category"] == "resource_exhaustion"
    assert "description" in info
    assert info["active"] is False


def test_registry_extensibility():
    """Verify that adding an arbitrary 6th fault works without changing existing implementations."""
    class CustomMemoryLeakFault(BaseFault):
        id = "memory_leak"
        name = "Simulated Memory Leak"
        description = "Simulates RSS memory consumption leak"
        target_service = "payments"
        category = "resource_exhaustion"

        def __init__(self):
            self._active = False

        def is_active(self) -> bool:
            return self._active

        async def activate(self, params=None):
            self._active = True
            return {"status": "activated"}

        async def deactivate(self):
            self._active = False
            return {"status": "deactivated"}

    custom_fault = CustomMemoryLeakFault()
    registry.register(custom_fault)

    assert registry.get("memory_leak") is not None
    assert registry.get("memory_leak").name == "Simulated Memory Leak"
