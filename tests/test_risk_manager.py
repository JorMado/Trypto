import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trypto.risk_manager import CryptoRiskManager

import pytest

@pytest.fixture
def mock_risk_params():
    return {
        'total_margin': 100000,
        'position_limits': {
            'BTC': {'max_size': 1.0, 'max_notional': 50000}
        }
    }

@pytest.fixture
def risk_manager(mock_risk_params):
    return CryptoRiskManager(risk_params=mock_risk_params)

@pytest.mark.asyncio
async def test_risk_monitoring(risk_manager):
    await risk_manager.monitor()
    # Verify that the risk manager is monitoring correctly
    assert risk_manager.is_active is True
    assert risk_manager.current_risk_level <= risk_manager.max_risk_threshold

def test_calculate_risk_exposure(risk_manager):
    positions = {
        'BTC/USDT': {'size': 0.5, 'price': 40000}
    }
    exposure = risk_manager._calculate_risk_exposure(positions)
    # Verify the exposure calculation
    expected_exposure = 0.5 * 40000  # 20000
    assert exposure == expected_exposure