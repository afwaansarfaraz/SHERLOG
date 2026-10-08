from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseFault(ABC):
    """Abstract base class representing an injectable fault scenario."""

    id: str
    name: str
    description: str
    target_service: str
    category: str  # resource_exhaustion, latency, dependency, traffic, configuration

    @abstractmethod
    async def activate(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Activate the fault with optional runtime tuning parameters."""
        pass

    @abstractmethod
    async def deactivate(self) -> Dict[str, Any]:
        """Deactivate the fault and return target service to baseline operation."""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Check whether the fault is currently active."""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Return structured metadata and current status."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target_service": self.target_service,
            "category": self.category,
            "active": self.is_active(),
        }
