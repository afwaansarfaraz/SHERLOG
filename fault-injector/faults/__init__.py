from faults.configuration_error import ConfigurationErrorFault
from faults.db_pool_exhaustion import DbPoolExhaustionFault
from faults.dependency_timeout import DependencyTimeoutFault
from faults.memory_leak import MemoryLeakFault
from faults.registry import registry
from faults.slow_query import SlowQueryFault
from faults.traffic_spike import TrafficSpikeFault

# Register initial 6 faults
registry.register(DbPoolExhaustionFault())
registry.register(SlowQueryFault())
registry.register(DependencyTimeoutFault())
registry.register(TrafficSpikeFault())
registry.register(ConfigurationErrorFault())
registry.register(MemoryLeakFault())

__all__ = ["registry"]
