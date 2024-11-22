import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from src.trypto.arbitrage_executor import ArbitrageExecutor  # Adjusted import

@pytest.fixture
def mock_exchanges():
    # Mock exchange interfaces
    return [...]

@pytest.mark.asyncio
async def test_arbitrage_execution(mock_exchanges):
    arbitrage_executor = ArbitrageExecutor(
        exchanges=mock_exchanges, 
        min_profit_threshold=0.002
    )
    # Mock potential arbitrage opportunities
    arbitrage_executor.find_opportunities = lambda: [
        {'pair': 'BTC/USDT', 'buy_exchange': 'ExchangeA', 'sell_exchange': 'ExchangeB', 'profit': 0.003}
    ]
    await arbitrage_executor.execute()
    # Verify trades were executed
    assert len(arbitrage_executor.completed_trades) > 0
    for trade in arbitrage_executor.completed_trades:
        assert trade['profit'] >= arbitrage_executor.min_profit_threshold