import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trypto.failover_system import FailoverSystem

import pytest

@pytest.fixture
def failover_system():
    return FailoverSystem()

def test_failover_initialization(failover_system):
    # Add assertions to test the initialization of the failover system
    assert failover_system is not None
    assert isinstance(failover_system, FailoverSystem)

@pytest.mark.asyncio
async def test_system_recovery(failover_system):
    # Simulate failure and test recovery
    failover_system.simulate_failure()
    assert failover_system.is_recovering is True

    await failover_system.recover()
    # Verify recovery
    assert failover_system.is_recovering is False
    assert failover_system.is_operational is True