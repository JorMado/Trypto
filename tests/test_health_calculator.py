import pytest
from src.trypto.health_calculator import HealthCalculator

@pytest.mark.asyncio
async def test_calculate_system_health():
    health_calculator = HealthCalculator()
    health = await health_calculator.calculate()
    health_dict = health.to_dict()
    
    assert isinstance(health_dict, dict)
    assert 'cpu_usage' in health_dict
    assert 'memory_usage' in health_dict
    assert 0 <= health_dict['cpu_usage'] <= 100
    assert 0 <= health_dict['memory_usage'] <= 100
    assert health_dict['status'] in ['healthy', 'degraded', 'unhealthy']
    
    await health_calculator.close()