import asyncio
import logging
from datetime import datetime

# Import existing modules
from arbitrage_executor import ArbitrageExecutor
from collateral_manager import CollateralManager
from connection_health import ConnectionHealth
from exchange_manager import ExchangeManager
from failover_system import FailoverSystem
from gasOracle import GasOracle
from health_calculator import HealthCalculator
from infrastructure import CryptoInfrastructure
from inventory_manager import InventoryManager
from market_maker import CryptoMarketMaker
from mev_protector import MEVProtector
from news_analyzer import NewsAnalyzer
from node_manager import NodeManager
from on_chain_analyzer import OnChainAnalyzer
from order_book_aggregator import OrderBookAggregator
from rate_limiter import RateLimiter
from retry_policy import RetryPolicy
from risk_manager import CryptoRiskManager
from sentiment_analyzer import CryptoSentimentAnalyzer
from sentiment_model import SentimentModel
from social_media_aggregator import SocialMediaAggregator
from system_monitor import SystemMonitor
from ws_feed_handler import WSFeedHandler
from config import MOCK_API_KEYS, MOCK_MODE, CONFIG

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

    async def initialize(self):
        try:
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
            self.logger.error(f"Initialization failed: {str(e)}")
            raise

    async def start(self):
        if self.running:
            return
            
        try:
            self.running = True
            self.logger.info("Starting trading system")
            
            # Start main loops
            await asyncio.gather(
                self.market_data_loop(),
                self.trading_loop(),
                self.risk_loop(),
                self.monitoring_loop()
            )
            
        except Exception as e:
            self.logger.error(f"Startup failed: {str(e)}")
            await self.shutdown()
            raise

    async def market_data_loop(self):
        while self.running:
            try:
                # Update market data with rate limiting
                if await self.rate_limiter.acquire('market_data'):
                    await self.retry_policy.execute(self._update_market_data)
            except Exception as e:
                self.logger.error(f"Market data error: {str(e)}")
                if self.should_emergency_shutdown(e):
                    await self.emergency_shutdown()
                    break
            await asyncio.sleep(0.1)  # 100ms interval

    async def _update_market_data(self):
        await asyncio.gather(
            self.orderbook.update(),
            self.ws_feed.process(),
            self.chain.analyze(),
            self.gas.update()
        )

    async def trading_loop(self):
        while self.running:
            try:
                # Execute trading strategies with proper awaits
                await asyncio.gather(
                    self.arbitrage.execute(),
                    self.market_maker.execute(),
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
                # Properly await all monitoring calls
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
            await self.exchange.close_all_positions()
            await self.exchange.cancel_all_orders()
            await self.shutdown()
        except Exception as e:
            self.logger.critical(f"Emergency shutdown failed: {str(e)}")
            self.running = False

    async def shutdown(self):
        self.logger.info("Graceful shutdown initiated")
        self.running = False
        
        try:
            await asyncio.gather(
                self.connection.shutdown(),
                self.arbitrage.shutdown(),
                self.collateral.shutdown(),
                self.exchange.shutdown(),
                self.failover.shutdown(),
                self.gas.shutdown(),
                self.health.shutdown(),
                self.infra.shutdown(),
                self.inventory.shutdown(),
                self.market_maker.shutdown(),
                self.mev.shutdown(),
                self.news.shutdown(),
                self.node.shutdown(),
                self.chain.shutdown(),
                self.orderbook.shutdown(),
                self.risk.shutdown(),
                self.sentiment.shutdown(),
                self.social.shutdown(),
                self.monitor.shutdown(),
                self.ws_feed.shutdown()
            )
        except Exception as e:
            self.logger.error(f"Shutdown error: {str(e)}")
            raise

    def should_emergency_shutdown(self, error: Exception) -> bool:
        return isinstance(error, (
            SystemError,
            RuntimeError,
            MemoryError,
            ConnectionError
        ))

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        system = TradingSystem()
        if await system.initialize():
            await system.start()
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())