import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.trypto.blockchain_monitor import BlockchainMonitor, BlockchainMetrics

import pytest

@pytest.fixture
async def blockchain_monitor():
    monitor = BlockchainMonitor()
    await monitor.initialize()
    return monitor  # Change yield to return since we don't need cleanup

@pytest.mark.asyncio
async def test_update_metrics(blockchain_monitor):
    metrics = await blockchain_monitor.update_metrics()
    metrics_dict = metrics.to_dict() if hasattr(metrics, 'to_dict') else vars(metrics)
    assert metrics_dict is not None
    assert all(key in metrics_dict for key in [
        'block_height',
        'gas_price',
        'mempool_size',
        'network_load'
    ])
    assert 'network_hash_rate' in metrics_dict

@pytest.mark.asyncio
async def test_get_network_status(blockchain_monitor):
    status = await blockchain_monitor.get_network_status()
    assert isinstance(status, dict)
    assert status['status'] in ['healthy', 'degraded', 'offline']