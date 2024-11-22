import asyncio
import logging
import time
from typing import Dict, Tuple, Any, List, Optional, Protocol
from enum import Enum
from datetime import datetime, timedelta
import aiohttp
import psutil

class HealthCheck:
    def __init__(self, name, check_func, timeout: float = 5.0):
        self.name = name
        self.check_func = check_func
        self.timeout = timeout

    async def run(self) -> Dict[str, Any]:
        try:
            async with asyncio.timeout(self.timeout):
                status, details = await self.check_func()
                return {'status': status, 'details': details}
        except asyncio.TimeoutError:
            return {'status': False, 'details': f"{self.name} check timed out after {self.timeout}s"}
        except Exception as e:
            return {'status': False, 'details': str(e)}

class NotificationLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class MonitoringAgent:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.notification_history: Dict[str, List[datetime]] = {}
        self.rate_limit_window = timedelta(minutes=5)
        self.webhook_url = "YOUR_WEBHOOK_URL"  # Configure as needed
        self.notification_count = 0
        self.last_notification_reset = datetime.now()

    def _should_notify(self, check_name: str) -> bool:
        now = datetime.now()
        if check_name not in self.notification_history:
            self.notification_history[check_name] = []
            return True

        # Clean up old notifications
        self.notification_history[check_name] = [
            t for t in self.notification_history[check_name]
            if now - t < self.rate_limit_window
        ]

        # Rate limiting logic
        if len(self.notification_history[check_name]) >= 3:
            return False

        self.notification_history[check_name].append(now)
        return True

    def _get_severity(self, details: Dict[str, Any]) -> NotificationLevel:
        if isinstance(details.get('error'), str):
            return NotificationLevel.CRITICAL
        return NotificationLevel.WARNING

    async def _send_webhook(self, message: str, level: NotificationLevel):
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "text": message,
                    "level": level.value,
                    "timestamp": datetime.now().isoformat()
                }
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status >= 400:
                        self.logger.error(f"Failed to send webhook: {await response.text()}")
        except Exception as e:
            self.logger.error(f"Webhook notification failed: {str(e)}")

    async def notify(self, check_name: str, details: Dict[str, Any]):
        if not self._should_notify(check_name):
            self.logger.debug(f"Notification rate limited for {check_name}")
            return

        level = self._get_severity(details)
        message = (
            f"Health Check Alert: {check_name}\n"
            f"Severity: {level.value}\n"
            f"Details: {details}\n"
            f"Time: {datetime.now().isoformat()}"
        )

        # Log the notification
        self.logger.warning(message)

        # Send webhook notification
        await self._send_webhook(message, level)

        # Update notification stats
        self.notification_count += 1

class SystemMonitor:
    def __init__(self):
        self.health_checks = []
        self.monitoring_agent = MonitoringAgent()
        self.running = False
        self._setup_logging()
        self.cpu_threshold = 90  # percentage
        self.memory_threshold = 90  # percentage
        self.logger = logging.getLogger(__name__)

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def register_health_check(self, health_check):
        self.health_checks.append(health_check)

    async def start_monitoring(self):
        self.running = True
        try:
            while self.running:
                for check in self.health_checks:
                    result = await check.run()
                    if not result['status']:
                        self.logger.error(f"Health check failed: {check.name}")
                        await self.monitoring_agent.notify(check.name, result['details'])
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            self.logger.info("Monitoring shutdown initiated")
            self.running = False

    async def stop_monitoring(self):
        self.running = False
        self.logger.info("Monitoring stopped")

    async def check(self):
        """Check system resources and performance"""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent()
            if cpu_percent > self.cpu_threshold:
                self.logger.warning(f"High CPU usage: {cpu_percent}%")

            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > self.memory_threshold:
                self.logger.warning(f"High memory usage: {memory.percent}%")

            # You can add more monitoring checks here
            
            return True

        except Exception as e:
            self.logger.error(f"System monitoring error: {str(e)}")
            return False

class ExchangeManager(Protocol):
    connections: Dict[str, Any]
    connection_health: Dict[str, Any]

class OrderBookAggregator(Protocol):
    last_updates: Dict[str, float]
    staleness_threshold: float

async def check_exchange_connections(exchange_manager: ExchangeManager) -> Tuple[bool, Dict[str, bool]]:
    try:
        all_connected = True
        details = {}
        for exchange_id, connection in exchange_manager.connections.items():
            is_connected = not exchange_manager.connection_health[exchange_id].missed_heartbeats
            details[exchange_id] = is_connected
            if not is_connected:
                all_connected = False
        return all_connected, details
    except AttributeError:
        return False, {"error": "Exchange manager not properly initialized"}

async def check_order_book_staleness(order_book_aggregator: OrderBookAggregator) -> Tuple[bool, Dict[str, bool]]:
    try:
        all_fresh = True
        details = {}
        for key, last_update in order_book_aggregator.last_updates.items():
            is_fresh = (time.time() - last_update) < order_book_aggregator.staleness_threshold
            details[key] = is_fresh
            if not is_fresh:
                all_fresh = False
        return all_fresh, details
    except AttributeError:
        return False, {"error": "Order book aggregator not properly initialized"}

# Initialize monitoring with proper dependency injection
def initialize_monitoring(exchange_mgr: ExchangeManager, order_book_agg: OrderBookAggregator) -> 'SystemMonitor':
    system_monitor = SystemMonitor()
    system_monitor.register_health_check(
        HealthCheck('Exchange Connections', lambda: check_exchange_connections(exchange_mgr))
    )
    system_monitor.register_health_check(
        HealthCheck('Order Book Staleness', lambda: check_order_book_staleness(order_book_agg))
    )
    return system_monitor