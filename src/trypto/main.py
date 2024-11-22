import asyncio
import signal
import logging
from datetime import datetime
import aiohttp
from collections import defaultdict

# Import existing modules
from trypto.arbitrage_executor import ArbitrageExecutor
from trypto.collateral_manager import CollateralManager
from trypto.connection_health import ConnectionHealth
from trypto.exchange_manager import ExchangeManager
from trypto.failover_system import FailoverSystem
from trypto.gasOracle import GasOracle
from trypto.health_calculator import HealthCalculator
from trypto.infrastructure import CryptoInfrastructure
from trypto.inventory_manager import InventoryManager
from trypto.market_maker import CryptoMarketMaker
from trypto.mev_protector import MEVProtector
from trypto.news_analyzer import NewsAnalyzer
from trypto.node_manager import NodeManager
from trypto.on_chain_analyzer import OnChainAnalyzer
from trypto.order_book_aggregator import OrderBookAggregator
from trypto.rate_limiter import RateLimiter
from trypto.retry_policy import RetryPolicy
from trypto.risk_manager import CryptoRiskManager
from trypto.sentiment_analyzer import CryptoSentimentAnalyzer
from trypto.sentiment_model import SentimentModel
from trypto.social_media_aggregator import SocialMediaAggregator
from trypto.system_monitor import SystemMonitor
from trypto.ws_feed_handler import WSFeedHandler
from trypto.config import MOCK_API_KEYS, MOCK_MODE, CONFIG

class TradingSystem:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running = False
        
        # Define trading pairs and risk parameters
        self.trading_pairs = [
            'BTC/USDT',
            'ETH/USDT',
            'SOL/USDT'
        ]
        
        self.market_maker_params = {
            'max_position_size': 1.0,
            'max_risk_per_trade': 0.02,
            'min_spread': 0.001,
            'max_spread': 0.01,
            'order_size_range': (0.001, 0.1),
            'volatility_adjustment': True
        }
        
        # Web3 and blockchain configuration
        self.web3_config = {
            'rpc_url': 'https://mainnet.infura.io/v3/YOUR-PROJECT-ID',  # Replace with actual Infura/RPC URL
            'chain_id': 1,  # 1 for Ethereum mainnet
            'gas_limit': 500000,
            'max_priority_fee': 2.5  # gwei
        }
        
        # Load private key securely - in production use env vars or secure key management
        self.private_key = 'YOUR-PRIVATE-KEY'  # Replace with secure key loading
        
        # Remove or comment out Web3 initialization in mock mode
        if not MOCK_MODE:
            from web3 import Web3
            self.web3 = Web3(Web3.HTTPProvider(self.web3_config['rpc_url']))
        
        # Extract node configuration from CONFIG
        primary_nodes = []
        fallback_nodes = []
        for chain_config in CONFIG['infrastructure']['nodes'].values():
            primary_nodes.extend(chain_config.get('primary', []))
            fallback_nodes.extend(chain_config.get('fallback', []))
        
        # Initialize components
        self.connection = ConnectionHealth()
        self.exchange = ExchangeManager()
        self.arbitrage = ArbitrageExecutor(exchanges=self.exchange, min_profit_threshold=0.002)
        self.collateral = CollateralManager(
            market_data_provider=self.exchange,
            risk_params={
                'margin_requirement': 0.1,
                'min_health_ratio': 1.1,
                'warning_threshold': 1.3
            }
        )
        self.failover = FailoverSystem()
        self.gas = GasOracle(api_keys=MOCK_API_KEYS['blockchain'] if MOCK_MODE else {})
        self.health = HealthCalculator()
        self.infra = CryptoInfrastructure()
        self.inventory = InventoryManager()
        self.market_maker = CryptoMarketMaker(
            pairs=self.trading_pairs,
            risk_params=self.market_maker_params
        )
        
        # Use mock MEV protector
        self.mev = MEVProtector()  # No need to pass web3 and private_key yet
        
        self.news = NewsAnalyzer(api_keys=MOCK_API_KEYS['news'] if MOCK_MODE else {})
        self.node = NodeManager(
            primary_nodes=primary_nodes,
            fallback_nodes=fallback_nodes
        )
        self.chain = OnChainAnalyzer(
            web3_provider=self.web3_config['rpc_url'] if not MOCK_MODE else None,
            api_keys=MOCK_API_KEYS['blockchain'] if MOCK_MODE else None
        )
        self.orderbook = OrderBookAggregator()
        self.risk = CryptoRiskManager(
            risk_params=CONFIG['risk_params']
        )
        self.sentiment = CryptoSentimentAnalyzer(api_keys=MOCK_API_KEYS['sentiment'] if MOCK_MODE else {})
        self.sentiment_model = SentimentModel()
        self.social = SocialMediaAggregator()
        self.monitor = SystemMonitor()
        
        # Initialize websocket connections for each exchange
        self.ws_connections = {
            'binance': 'wss://stream.binance.com:9443/ws',
            'coinbase': 'wss://ws-feed.pro.coinbase.com',
            # Add more exchanges as needed
        }

        # Initialize websocket handler with primary exchange
        self.ws_feed = WSFeedHandler(
            websocket=self.ws_connections['binance'],
            exchange_id='binance'
        )
        
        self.retry_policy = RetryPolicy()
        self.rate_limiter = RateLimiter()
        self.session = None  # Add aiohttp session property
        self.sessions = {}  # Track all client sessions
        self.error_counts = defaultdict(int)  # Add error counter
        self.error_log_threshold = 3  # Only log first N occurrences
        self.health_stats = {
            'market_data_updates': 0,
            'trade_executions': 0,
            'errors': defaultdict(int),
            'last_health_check': datetime.now()
        }

    async def initialize(self):
        try:
            # Create shared aiohttp session
            self.sessions['main'] = aiohttp.ClientSession()
            
            self.logger.info("Initializing Trading System")
            
            # Initialize components one by one to better handle failures
            components = [
                (self.connection, "ConnectionHealth"),
                (self.exchange, "ExchangeManager"),
                (self.arbitrage, "ArbitrageExecutor"),
                (self.collateral, "CollateralManager"),
                (self.failover, "FailoverSystem"),
                (self.gas, "GasOracle"),
                (self.health, "HealthCalculator"),
                (self.infra, "CryptoInfrastructure"),
                (self.inventory, "InventoryManager"),
                (self.market_maker, "CryptoMarketMaker"),
                (self.mev, "MEVProtector"),
                (self.news, "NewsAnalyzer"),
                (self.node, "NodeManager"),
                (self.chain, "OnChainAnalyzer"),
                (self.orderbook, "OrderBookAggregator"),
                (self.risk, "CryptoRiskManager"),
                (self.sentiment, "CryptoSentimentAnalyzer"),
                (self.social, "SocialMediaAggregator"),
                (self.monitor, "SystemMonitor"),
                (self.ws_feed, "WSFeedHandler")
            ]

            for component, name in components:
                try:
                    if hasattr(component, 'initialize'):
                        await component.initialize()
                        self.logger.info(f"Initialized {name}")
                    else:
                        self.logger.warning(f"{name} has no initialize method")
                except Exception as e:
                    self.logger.error(f"Failed to initialize {name}: {str(e)}")
                    raise
            
            self.logger.info("System initialized successfully")
            return True
            
        except Exception as e:
            await self._cleanup_sessions()
            self.logger.error(f"Initialization failed: {str(e)}")
            raise

    async def _cleanup_sessions(self):
        """Helper method to properly close all sessions"""
        try:
            # First cleanup component sessions in parallel
            cleanup_tasks = []
            
            components_with_sessions = [
                self.orderbook,
                self.ws_feed,
                self.news,
                self.chain,
                self.sentiment,
                self.monitor,
                self.social,
                self.gas,
                self.node,
                self.exchange,  # Add exchange manager
                self.collateral  # Add collateral manager
            ]
            
            for component in components_with_sessions:
                if hasattr(component, 'cleanup_session'):
                    task = asyncio.create_task(component.cleanup_session())
                    cleanup_tasks.append(task)

            if cleanup_tasks:
                await asyncio.wait(cleanup_tasks, timeout=5.0)

            # Then cleanup main sessions
            session_tasks = []
            for session in self.sessions.values():
                if session and not session.closed:
                    task = asyncio.create_task(session.close())
                    session_tasks.append(task)
            
            if session_tasks:
                await asyncio.wait(session_tasks, timeout=5.0)
            
            self.sessions.clear()
            
        except Exception as e:
            self.logger.error(f"Session cleanup error: {e}")

    async def start(self):
        if self.running:
            return
            
        try:
            self.running = True
            self.logger.info("Starting trading system")
            
            # Create tasks and store their references
            self.tasks = [
                asyncio.create_task(self.market_data_loop()),
                asyncio.create_task(self.trading_loop()),
                asyncio.create_task(self.risk_loop()),
                asyncio.create_task(self.monitoring_loop())
            ]
            
            # Wait for all tasks to complete or for cancellation
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except asyncio.CancelledError:
            self.logger.info("System shutdown requested")
        except Exception as e:
            self.logger.error(f"Startup failed: {str(e)}")
        finally:
            await self.shutdown()

    async def _update_market_data(self):
        """Update market data with error throttling"""
        try:
            results = await asyncio.gather(
                self.orderbook.update(),
                self.ws_feed.process(),
                self.chain.analyze(),
                self.gas.update(),
                return_exceptions=True
            )
            
            # Update health stats
            self.health_stats['market_data_updates'] += 1
            self.health_stats['last_health_check'] = datetime.now()
            
            # Reset error counts on successful update
            self.error_counts.clear()
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    error_key = f"market_data_{i}"
                    self.error_counts[error_key] += 1
                    
                    # Only log first N occurrences
                    if self.error_counts[error_key] <= self.error_log_threshold:
                        self.logger.warning(f"Market data component {i} error: {result}")
                    elif self.error_counts[error_key] == self.error_log_threshold + 1:
                        self.logger.warning(f"Suppressing further market data errors for component {i}")
                    
                    if not MOCK_MODE:
                        raise result
                        
        except Exception as e:
            self.health_stats['errors']['market_data'] += 1
            if not MOCK_MODE:
                raise
            # In mock mode, only log occasional errors
            error_key = "mock_mode_error"
            self.error_counts[error_key] += 1
            if self.error_counts[error_key] <= self.error_log_threshold:
                self.logger.debug(f"Mock mode market data error: {e}")

    async def market_data_loop(self):
        while self.running:
            try:
                if await self.rate_limiter.acquire('market_data'):
                    async with asyncio.timeout(5):
                        await self.retry_policy.execute(self._update_market_data)
            except asyncio.TimeoutError:
                self.logger.warning("Market data update timed out")
            except Exception as e:
                if self.should_emergency_shutdown(e):
                    await self.emergency_shutdown()
                    break
                # Only log non-mock errors
                if not MOCK_MODE or not str(e).startswith("Simulated"):
                    self.logger.error(f"Market data error: {str(e)}")
            await asyncio.sleep(0.5)  # Increase sleep time in mock mode

    async def trading_loop(self):
        while self.running:
            try:
                # Properly await market maker execution
                await self.market_maker.execute()
                
                # Execute other trading strategies
                await asyncio.gather(
                    self.arbitrage.execute(),
                    self.inventory.rebalance()
                )
            except Exception as e:
                self.logger.error(f"Trading error: {str(e)}")
                if self.should_emergency_shutdown(e):
                    await self.emergency_shutdown()
                    break
            await asyncio.sleep(0.05)  # 50ms interval

    async def risk_loop(self):
        while self.running:
            try:
                await asyncio.gather(
                    self.risk.monitor(),
                    self.collateral.manage(),
                    self.health.calculate()
                )
            except Exception as e:
                self.logger.error(f"Risk monitoring error: {str(e)}")
                if self.should_emergency_shutdown(e):
                    await self.emergency_shutdown()
                    break
            await asyncio.sleep(1)  # 1s interval

    async def monitoring_loop(self):
        while self.running:
            try:
                stats = await self._get_system_health()
                self.logger.info(f"System Health: {stats}")
                
                # Regular health checks
                await asyncio.gather(
                    self.monitor.check(),
                    self.connection.check(),
                    self.node.monitor(),
                    self.failover.check()
                )
            except Exception as e:
                self.logger.error(f"System monitoring error: {str(e)}")
                if self.should_emergency_shutdown(e):
                    await self.emergency_shutdown()
                    break
            await asyncio.sleep(1)  # 1s interval

    async def emergency_shutdown(self):
        self.logger.critical("Emergency shutdown initiated")
        try:
            # First close sessions
            await self._cleanup_sessions()
            
            # Then handle emergency actions
            async with asyncio.TaskGroup() as tg:
                if hasattr(self.exchange, 'close_all_positions'):
                    tg.create_task(
                        asyncio.wait_for(
                            self.exchange.close_all_positions(),
                            timeout=5.0
                        )
                    )
                if hasattr(self.exchange, 'cancel_all_orders'):
                    tg.create_task(
                        asyncio.wait_for(
                            self.exchange.cancel_all_orders(),
                            timeout=5.0
                        )
                    )
        except* (asyncio.TimeoutError, Exception) as e:
            self.logger.critical(f"Emergency shutdown tasks failed: {e!r}")
        finally:
            await self.shutdown()

    async def shutdown(self):
        if not self.running:
            return
            
        self.logger.info("Graceful shutdown initiated")
        self.running = False
        
        try:
            # First stop all running tasks
            if hasattr(self, 'tasks'):
                await asyncio.wait(
                    [asyncio.create_task(self._cancel_task(task)) for task in self.tasks],
                    timeout=5.0
                )
            
            # Then cleanup sessions
            await self._cleanup_sessions()
            
            # Finally shutdown components
            components = [
                self.connection, self.arbitrage, self.collateral,
                self.exchange, self.failover, self.gas,
                self.health, self.infra, self.inventory,
                self.market_maker, self.mev, self.news,
                self.node, self.chain, self.orderbook,
                self.risk, self.sentiment, self.social,
                self.monitor, self.ws_feed
            ]
            
            await asyncio.wait(
                [
                    asyncio.create_task(self._shutdown_component(component))
                    for component in components
                ],
                timeout=10.0
            )
                
        except Exception as e:
            self.logger.error(f"Shutdown error: {str(e)}")
        finally:
            # Final check for any remaining tasks
            tasks = [t for t in asyncio.all_tasks() 
                    if t is not asyncio.current_task()]
            if tasks:
                await asyncio.wait(tasks, timeout=1.0)

    async def _cancel_task(self, task):
        """Helper method to cancel a task safely"""
        if not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    async def _shutdown_component(self, component):
        """Helper method to shutdown a component safely"""
        try:
            # First cleanup any sessions
            if hasattr(component, 'cleanup_session'):
                try:
                    await asyncio.wait_for(component.cleanup_session(), timeout=5.0)
                except Exception as e:
                    self.logger.error(f"Session cleanup failed for {component.__class__.__name__}: {e}")
            
            # Then shutdown component
            if hasattr(component, 'shutdown') and callable(component.shutdown):
                result = component.shutdown()
                if asyncio.iscoroutine(result):
                    await asyncio.wait_for(result, timeout=5.0)
        except Exception as e:
            self.logger.error(f"Error shutting down {component.__class__.__name__}: {e}")

    def should_emergency_shutdown(self, error: Exception) -> bool:
        # Don't trigger emergency shutdown for mock mode errors
        if MOCK_MODE and str(error).startswith("Simulated"):
            return False
            
        return isinstance(error, (
            SystemError,
            RuntimeError,
            MemoryError,
            ConnectionError
        ))

    async def _get_system_health(self) -> dict:
        """Get system health metrics"""
        return {
            'uptime': (datetime.now() - self.health_stats['last_health_check']).seconds,
            'market_data_updates': self.health_stats['market_data_updates'],
            'trade_executions': self.health_stats['trade_executions'],
            'error_counts': dict(self.health_stats['errors']),
            'components': {
                'orderbook': await self.orderbook.get_health(),
                'market_maker': await self.market_maker.get_health(),
                'risk': await self.risk.get_health()
            }
        }

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Set a higher recursion limit if needed
    import sys
    sys.setrecursionlimit(1500)
    
    # Setup signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown(loop, sig)))
    
    system = None
    try:
        system = TradingSystem()
        if await system.initialize():
            await system.start()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
    finally:
        if system:
            await system.shutdown()

async def shutdown(loop, signal):
    """Cleanup tasks tied to the service's shutdown."""
    logger = logging.getLogger(__name__)
    logger.info(f"Received exit signal {signal.name}")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

if __name__ == "__main__":
    asyncio.run(main())