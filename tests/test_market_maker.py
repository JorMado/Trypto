import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trypto.market_maker import CryptoMarketMaker

import pytest

@pytest.fixture
def mock_market_data():
    return {
        'BTC/USDT': {'bid': 40000, 'ask': 40100},
        'ETH/USDT': {'bid': 2200, 'ask': 2210}
    }

@pytest.fixture
def mock_order_book():
    return {
        'bids': [[40000, 1.0], [39900, 2.0]],
        'asks': [[40100, 1.0], [40200, 2.0]]
    }

@pytest.mark.asyncio
async def test_order_placement(mock_market_data, mock_order_book):
    market_maker = CryptoMarketMaker(
        pairs=['BTC/USDT'],
        risk_params={'max_position_size': 1.0}
    )
    # Mock market data and order book if necessary
    market_maker.market_data = mock_market_data
    market_maker.order_book = mock_order_book

    await market_maker.execute()
    # Verify that orders were placed
    assert len(market_maker.open_orders) > 0
    for order in market_maker.open_orders:
        assert order['pair'] in market_maker.pairs
        assert order['size'] <= market_maker.risk_params['max_position_size']