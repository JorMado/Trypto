import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trypto.exchange_manager import ExchangeManager

import pytest

@pytest.fixture
def mock_exchange_manager():
    # Mock ExchangeManager instance
    return ExchangeManager()

@pytest.mark.asyncio
async def test_place_order(mock_exchange_manager):
    # Place a test order
    order = await mock_exchange_manager.place_order(
        symbol='BTC/USDT',
        order_type='limit',
        side='buy',
        amount=0.1,
        price=40000
    )
    # Verify order placement
    assert order is not None
    assert order['status'] == 'open'
    assert order['symbol'] == 'BTC/USDT'
    assert order['amount'] == 0.1

@pytest.mark.asyncio
async def test_close_all_positions(mock_exchange_manager):
    # Assume positions are open
    mock_exchange_manager.positions = [{'symbol': 'BTC/USDT', 'amount': 0.1}]
    await mock_exchange_manager.close_all_positions()
    # Verify positions are closed
    assert mock_exchange_manager.positions == []