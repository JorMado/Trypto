# infrastructure.py
from node_manager import NodeManager, NodeConfig
from failover_system import FailoverSystem, FailoverConfig
from typing import Dict, Optional
import logging

class CryptoInfrastructure:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger('CryptoInfrastructure')
        
        # Initialize components
        self.node_managers = self._setup_node_managers()
        self.failover_system = FailoverSystem(
            FailoverConfig(**self.config.get('failover', {}))
        )
        
    def _setup_node_managers(self) -> Dict[str, NodeManager]:
        """Setup node managers for each chain"""
        node_managers = {}
        node_configs = self.config.get('nodes', {})
        
        for chain, chain_config in node_configs.items():
            primary_nodes = [
                NodeConfig(**node_config)
                for node_config in chain_config.get('primary', [])
            ]
            fallback_nodes = [
                NodeConfig(**node_config)
                for node_config in chain_config.get('fallback', [])
            ]
            
            node_managers[chain] = NodeManager(
                primary_nodes=primary_nodes,
                fallback_nodes=fallback_nodes
            )
            
        return node_managers
        
    async def initialize(self):
        """Initialize the infrastructure"""
        for chain, manager in self.node_managers.items():
            await manager.initialize()
            
        await self.failover_system.start_monitoring(self.node_managers)
        
    async def close(self):
        """Cleanup resources"""
        for manager in self.node_managers.values():
            await manager.close()
            
        await self.failover_system.stop_monitoring()