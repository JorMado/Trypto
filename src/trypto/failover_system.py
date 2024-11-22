# failover_system.py
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import time
from node_manager import NodeManager, NodeStatus

@dataclass
class FailoverConfig:
    check_interval: int = 60  # seconds
    health_threshold: float = 0.7
    recovery_threshold: float = 0.85
    max_retry_attempts: int = 3
    retry_delay: int = 5  # seconds
    failback_delay: int = 300  # seconds
    maintenance_window: Dict[str, str] = None  # e.g., {'start': '02:00', 'end': '04:00'}
    retry_interval: int = 5  # seconds

@dataclass
class FailoverState:
    is_active: bool
    last_failover: Optional[datetime]
    failover_count: int
    current_primary: str
    last_health_check: datetime
    recovery_start: Optional[datetime]

class FailoverSystem:
    def __init__(self, config: Optional[FailoverConfig] = None):
        self.config = config or FailoverConfig()
        self.node_managers: Dict[str, NodeManager] = {}
        self.states: Dict[str, FailoverState] = {}
        self.is_running = False
        self.lock = asyncio.Lock()
        self.components = {}
        self.health_status = {}
        
        # Setup logging
        self.logger = logging.getLogger('FailoverSystem')
        self.logger.setLevel(logging.INFO)
        
    async def start_monitoring(self, node_managers: Dict[str, NodeManager]):
        """Start monitoring node managers for failover"""
        self.node_managers = node_managers
        self.is_running = True
        
        # Initialize states for each chain
        for chain, manager in node_managers.items():
            current_node = await manager.get_current_node()
            self.states[chain] = FailoverState(
                is_active=False,
                last_failover=None,
                failover_count=0,
                current_primary=current_node.url if current_node else None,
                last_health_check=datetime.now(),
                recovery_start=None
            )
            
        # Start monitoring tasks
        await self._start_monitoring_tasks()
        
    async def stop_monitoring(self):
        """Stop the failover monitoring"""
        self.is_running = False
        
    async def _start_monitoring_tasks(self):
        """Start monitoring tasks for each chain"""
        tasks = []
        for chain in self.node_managers.keys():
            tasks.append(self._monitor_chain(chain))
            
        await asyncio.gather(*tasks)
        
    async def _monitor_chain(self, chain: str):
        """Monitor a specific blockchain network"""
        while self.is_running:
            try:
                if not self._is_in_maintenance_window():
                    await self._check_chain_health(chain)
                await asyncio.sleep(self.config.check_interval)
            except Exception as e:
                self.logger.error(f"Error monitoring chain {chain}: {str(e)}")
                await asyncio.sleep(self.config.retry_delay)
                
    async def _check_chain_health(self, chain: str):
        """Check health of a specific chain and handle failover if needed"""
        async with self.lock:
            manager = self.node_managers[chain]
            state = self.states[chain]
            
            # Get current node status
            current_node = await manager.get_current_node()
            if not current_node:
                await self._handle_no_active_node(chain)
                return
                
            status = manager.get_node_status(current_node.url)
            if not status:
                await self._handle_no_status(chain)
                return
                
            # Update last health check
            state.last_health_check = datetime.now()
            
            # Check if health score is below threshold
            if status.health_score < self.config.health_threshold:
                await self._initiate_failover(chain, status)
            elif (state.is_active and 
                  status.health_score >= self.config.recovery_threshold):
                await self._attempt_recovery(chain)
                
    async def _initiate_failover(self, chain: str, status: NodeStatus):
        """Initiate failover process for a chain"""
        state = self.states[chain]
        manager = self.node_managers[chain]
        
        # Check if we've exceeded max retry attempts
        if (state.failover_count >= self.config.max_retry_attempts and
            datetime.now() - state.last_failover < timedelta(minutes=5)):
            self.logger.critical(
                f"Max failover attempts reached for {chain}. "
                "Manual intervention required."
            )
            return
            
        self.logger.warning(
            f"Initiating failover for {chain}. "
            f"Health score: {status.health_score}"
        )
        
        # Attempt to switch to a healthy node
        success = await manager.force_node_switch()
        if success:
            state.is_active = True
            state.last_failover = datetime.now()
            state.failover_count += 1
            new_node = await manager.get_current_node()
            self.logger.info(
                f"Failover successful for {chain}. "
                f"New node: {new_node.url}"
            )
        else:
            self.logger.error(
                f"Failover failed for {chain}. No healthy nodes available."
            )
            
    async def _attempt_recovery(self, chain: str):
        """Attempt to recover to primary node"""
        state = self.states[chain]
        manager = self.node_managers[chain]
        
        # Check if enough time has passed since failover
        if (state.last_failover and 
            datetime.now() - state.last_failover < timedelta(
                seconds=self.config.failback_delay
            )):
            return
            
        # Check primary node health
        primary_nodes = manager.primary_nodes
        for node in primary_nodes:
            status = manager.get_node_status(node.url)
            if status and status.health_score >= self.config.recovery_threshold:
                # Attempt to switch back to primary
                success = await self._switch_to_node(chain, node)
                if success:
                    state.is_active = False
                    state.recovery_start = None
                    state.failover_count = 0
                    self.logger.info(
                        f"Successfully recovered to primary node for {chain}"
                    )
                    break
                
    async def _switch_to_node(self, chain: str, node) -> bool:
        """Attempt to switch to a specific node"""
        try:
            manager = self.node_managers[chain]
            current = await manager.get_current_node()
            
            if current and current.url == node.url:
                return True
                
            # Verify node health before switching
            status = await manager._check_node_health(node)
            if status.health_score >= self.config.health_threshold:
                manager.current_node = node
                manager.is_operational = True
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error switching to node: {str(e)}")
            return False
            
    async def _handle_no_active_node(self, chain: str):
        """Handle case where no active node is available"""
        self.logger.critical(f"No active node for {chain}. Attempting recovery...")
        manager = self.node_managers[chain]
        
        # Try all available nodes
        all_nodes = manager.primary_nodes + manager.fallback_nodes
        for node in all_nodes:
            if await self._switch_to_node(chain, node):
                self.logger.info(f"Successfully recovered active node for {chain}")
                return
                
        self.logger.critical(f"Failed to recover any nodes for {chain}")
        
    async def _handle_no_status(self, chain: str):
        """Handle case where node status is unavailable"""
        self.logger.error(f"No status available for current node in {chain}")
        await self._initiate_failover(chain, NodeStatus(
            is_synced=False,
            block_height=0,
            peers=0,
            latency=float('inf'),
            last_updated=datetime.now(),
            health_score=0.0
        ))
        
    def _is_in_maintenance_window(self) -> bool:
        """Check if current time is within maintenance window"""
        if not self.config.maintenance_window:
            return False
            
        now = datetime.now().time()
        start = datetime.strptime(
            self.config.maintenance_window['start'], 
            '%H:%M'
        ).time()
        end = datetime.strptime(
            self.config.maintenance_window['end'], 
            '%H:%M'
        ).time()
        
        if start <= end:
            return start <= now <= end
        else:  # Maintenance window crosses midnight
            return now >= start or now <= end
            
    async def get_failover_status(self, chain: str) -> Dict:
        """Get current failover status for a chain"""
        if chain not in self.states:
            return None
            
        state = self.states[chain]
        manager = self.node_managers[chain]
        current_node = await manager.get_current_node()
        
        return {
            'is_active': state.is_active,
            'current_node': current_node.url if current_node else None,
            'failover_count': state.failover_count,
            'last_failover': state.last_failover,
            'last_health_check': state.last_health_check,
            'recovery_start': state.recovery_start,
            'health_score': manager.get_node_status(current_node.url).health_score
            if current_node else 0.0
        }
        
    async def force_failover(self, chain: str) -> bool:
        """Force a failover for a specific chain"""
        if chain not in self.node_managers:
            return False
            
        async with self.lock:
            status = NodeStatus(
                is_synced=False,
                block_height=0,
                peers=0,
                latency=float('inf'),
                last_updated=datetime.now(),
                health_score=0.0
            )
            await self._initiate_failover(chain, status)
            
        return True

    async def initialize(self):
        """Initialize failover system"""
        self.logger.info("Initializing failover system")
        # Add initialization logic here

    async def check(self) -> bool:
        """Check system health and trigger failover if needed"""
        try:
            for component_id, component in self.components.items():
                status = await self._check_component(component)
                self.health_status[component_id] = status
                
                if not status:
                    await self._handle_failover(component_id)
            return True
        except Exception as e:
            self.logger.error(f"Failover check failed: {str(e)}")
            return False

    async def _check_component(self, component: Any) -> bool:
        """Check individual component health"""
        # Implement component health check logic
        return True

    async def _handle_failover(self, component_id: str):
        """Handle failover for a failed component"""
        self.logger.warning(f"Initiating failover for component: {component_id}")
        # Implement failover logic here