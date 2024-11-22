import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from src.trypto.on_chain_analyzer import OnChainAnalyzer

@pytest.fixture
def on_chain_analyzer():
    return OnChainAnalyzer()

@pytest.mark.asyncio
async def test_on_chain_analysis(on_chain_analyzer):
    result = await on_chain_analyzer.analyze()
    # Verify the result contains expected keys
    assert isinstance(result, dict)
    assert 'transaction_volume' in result
    assert 'active_addresses' in result
    assert result['transaction_volume'] > 0
    assert result['active_addresses'] > 0