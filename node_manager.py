# node_manager.py
import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import time

@dataclass
class NodeStatus:
    is_synced: bool
    block_height: int
    peers: int
    latency: float
    last_updated: datetime
    health_score: float

@dataclass
class NodeConfig:
    url: str
    chain: str
    type: str  # 'primary' or 'fallback'
    weight: float
    max_latency: float
    min_peers: int
    required_block_height: Optional[int] = None

class NodeManager:
    def __init__(self, primary_nodes: List[Dict], fallback_nodes: List[Dict]):
        self.primary_nodes = primary_nodes
        self.fallback_nodes = fallback_nodes
        self.active_nodes = []
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        try:
            self.logger.info("Initializing node manager")
            await self._initialize_nodes()
        except Exception as e:
            self.logger.error(f"Node manager initialization failed: {str(e)}")
            raise

    async def _initialize_nodes(self):
        for node in self.primary_nodes:
            try:
                status = await self._check_node_health(node)
                if status:
                    self.active_nodes.append(node)
                    self.logger.info(f"Primary node {node['url']} initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize node {node['url']}: {str(e)}")

        if not self.active_nodes:
            for node in self.fallback_nodes:
                try:
                    status = await self._check_node_health(node)
                    if status:
                        self.active_nodes.append(node)
                        self.logger.info(f"Fallback node {node['url']} initialized successfully")
                except Exception as e:
                    self.logger.error(f"Failed to initialize fallback node {node['url']}: {str(e)}")

        if not self.active_nodes:
            raise RuntimeError("No nodes could be initialized")

    async def _check_node_health(self, node: Dict[str, Any]) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(node['url'], timeout=5) as response:
                    return response.status == 200
        except Exception as e:
            self.logger.error(f"Health check failed for {node['url']}: {str(e)}")
            return False

    async def monitor(self):
        for node in self.active_nodes[:]:  # Create a copy of the list to iterate
            if not await self._check_node_health(node):
                self.active_nodes.remove(node)
                self.logger.warning(f"Node {node['url']} removed from active nodes")
                
                # Try to replace with a fallback node
                for fallback in self.fallback_nodes:
                    if fallback not in self.active_nodes:
                        if await self._check_node_health(fallback):
                            self.active_nodes.append(fallback)
                            self.logger.info(f"Added fallback node {fallback['url']}")
                            break

    async def shutdown(self):
        self.logger.info("Shutting down node manager")
        self.active_nodes.clear()

# Example configuration
ETHEREUM_NODES = {
    'primary': [
        {
            "url": "https://mainnet.infura.io/v3/your-key",
            "chain": "ethereum",
            "type": "primary",
            "weight": 1.0,
            "max_latency": 1.0,
            "min_peers": 25
        },
        {
            "url": "https://eth-mainnet.alchemyapi.io/v2/your-key",
            "chain": "ethereum",
            "type": "primary",
            "weight": 1.0,
            "max_latency": 1.0,
            "min_peers": 25
        }
    ],
    'fallback': [
        {
            "url": "https://eth-mainnet.g.alchemy.com/v2/your-key",
            "chain": "ethereum",
            "type": "fallback",
            "weight": 0.8,
            "max_latency": 2.0,
            "min_peers": 10
        }
    ]
}