import pytest
import pytest_asyncio
import asyncio

@pytest_asyncio.fixture(scope="function")
async def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    await _cleanup_loop(loop)
    loop.close()

async def _cleanup_loop(loop):
    """Clean up any pending tasks on the loop."""
    tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
    if tasks:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

@pytest.fixture
def mock_metrics():
    """Common metrics fixture for tests."""
    return {
        'network_hash_rate': 150000000,
        'block_height': 12345,
        'gas_price': 50,
        'mempool_size': 1000,
        'network_load': 0.75
    }