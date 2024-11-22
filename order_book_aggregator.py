import asyncio
import time
import logging
from collections import defaultdict
from cachetools import LRUCache
from typing import Dict, Any
from datetime import datetime

class OrderBookAggregator:
    def __init__(self):
        self.order_books = defaultdict(dict)
        self.best_prices = {}
        self.last_updates = {}
        self.staleness_threshold = 5.0  # seconds
        self.depth_cache = LRUCache(maxsize=1000)
        self.locks = defaultdict(asyncio.Lock)
        self.logger = logging.getLogger(__name__)

    async def update_order_book(self, exchange, symbol, data):
        async with self._get_lock(exchange, symbol):
            if not self._is_valid_update(data):
                logging.warning(f"Invalid update for {exchange}:{symbol}")
                await self._request_snapshot(exchange, symbol)
                return

            current_version = self.order_books[exchange][symbol].get('version', 0)
            if data.get('version', 0) <= current_version:
                return

            self.order_books[exchange][symbol] = data
            self.last_updates[f"{exchange}:{symbol}"] = time.time()

            await self._update_best_prices(symbol)
            await self._update_depth_cache(exchange, symbol)

    async def update(self):
        """Update order book data from all sources"""
        try:
            # Implement order book update logic here
            for exchange_id, order_book in self.order_books.items():
                # Update timestamp
                self.last_updates[exchange_id] = datetime.now().timestamp()
            return True
        except Exception as e:
            self.logger.error(f"Failed to update order books: {str(e)}")
            return False

    def _get_lock(self, exchange, symbol):
        key = f"{exchange}:{symbol}"
        return self.locks[key]

    def _is_stale(self, exchange, symbol):
        last_update = self.last_updates.get(f"{exchange}:{symbol}", 0)
        return (time.time() - last_update) > self.staleness_threshold

    def get_global_liquidity(self, symbol, depth=10):
        cache_key = f"{symbol}:{depth}"
        cached_result = self.depth_cache.get(cache_key)
        if cached_result:
            return cached_result

        result = self._calculate_global_liquidity(symbol, depth)
        self.depth_cache[cache_key] = result
        return result

    def _is_valid_update(self, data):
        return 'bids' in data and 'asks' in data and 'version' in data

    async def _request_snapshot(self, exchange, symbol):
        # Request a fresh snapshot from the exchange's REST API
        session = self.exchange_manager.connections[exchange]
        url = f"{self.exchange_manager.exchange_configs[exchange]['rest_endpoint']}/depth?symbol={symbol}"
        async with session.get(url) as response:
            snapshot = await response.json()
            await self.update_order_book(exchange, symbol, snapshot)

    def _aggregate_levels(self, aggregated, book, depth):
        for price, volume in book['bids'][:depth]:
            aggregated['bids'][price] += volume
        for price, volume in book['asks'][:depth]:
            aggregated['asks'][price] += volume

    def _sort_and_trim(self, aggregated, depth):
        bids = sorted(aggregated['bids'].items(), key=lambda x: -float(x[0]))[:depth]
        asks = sorted(aggregated['asks'].items(), key=lambda x: float(x[0]))[:depth]
        return {'bids': bids, 'asks': asks, 'timestamp': aggregated['timestamp']}

    # ...existing methods...