import logging
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from trypto.base_component import BaseComponent

@dataclass
class BlockchainMetrics:
    network_hash_rate: int
    block_height: int
    gas_price: int
    mempool_size: int
    network_load: float

    def to_dict(self):
        return asdict(self)

class BlockchainMonitor(BaseComponent):
    def __init__(self, chain_id=1):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.chain_id = chain_id
        self.status = {}
        self.last_block = None
        
    async def initialize(self):
        self.logger.info(f"Initializing BlockchainMonitor for chain {self.chain_id}")
        self.status = {
            'chain_id': self.chain_id,
            'is_healthy': True,
            'last_block': None,
            'sync_status': None
        }
        return True
        
    async def update_metrics(self) -> BlockchainMetrics:
        return self.metrics
        
    async def get_network_status(self) -> dict:
        return {
            'status': 'healthy',
            'latency': 100,
            'peers': 30
        }
        
    async def shutdown(self):
        self.logger.info("Shutting down blockchain monitor")
        return True