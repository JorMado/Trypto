# config.py

from typing import Dict, List, Any
import os
from dataclasses import dataclass

@dataclass
class NetworkConfig:
    url: str
    chain_id: int
    max_gas_price: int
    confirmation_blocks: int
    timeout: int

class ConfigurationManager:
    @staticmethod
    def get_env_or_default(key: str, default: str) -> str:
        return os.getenv(key, default)

MOCK_API_KEYS = {
    'news': {
        'newsapi': 'mock_newsapi_key',
        'bloomberg': 'mock_bloomberg_key',
        'reuters': 'mock_reuters_key'
    },
    'sentiment': {
        'twitter': 'mock_twitter_key',
        'reddit': 'mock_reddit_key'
    },
    'market': {
        'binance': 'mock_binance_key',
        'coinbase': 'mock_coinbase_key',
        'ftx': 'mock_ftx_key'
    },
    'blockchain': {
        'etherscan': 'mock_etherscan_key',
        'infura': 'mock_infura_key'
    }
}

MOCK_MODE = True  # Set to False in production

CONFIG = {
    'exchange_credentials': {
        'binance': {
            'api_key': ConfigurationManager.get_env_or_default('BINANCE_API_KEY', 'your_binance_api_key'),
            'api_secret': ConfigurationManager.get_env_or_default('BINANCE_API_SECRET', 'your_binance_api_secret')
        },
        'coinbase': {
            'api_key': ConfigurationManager.get_env_or_default('COINBASE_API_KEY', 'your_coinbase_api_key'),
            'api_secret': ConfigurationManager.get_env_or_default('COINBASE_API_SECRET', 'your_coinbase_api_secret')
        },
        'kraken': {
            'api_key': ConfigurationManager.get_env_or_default('KRAKEN_API_KEY', 'your_kraken_api_key'),
            'api_secret': ConfigurationManager.get_env_or_default('KRAKEN_API_SECRET', 'your_kraken_api_secret')
        }
    },
    
    'exchanges': ['binance', 'coinbase', 'kraken'],
    
    'market_data_channels': {
        'realtime': ['ticker', 'orderBook', 'trades'],
        'depth': ['level2', 'level3'],
        'intervals': ['1m', '5m', '15m', '1h', '4h', '1d']
    },
    
    'trading_pairs': {
        'primary': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
        'secondary': ['ETH/BTC', 'BNB/BTC'],
        'defi': ['UNI/USDT', 'AAVE/USDT', 'LINK/USDT']
    },
    
    'risk_params': {
        'position_limits': {
            'BTC': {'max_size': 1.0, 'max_notional': 50000},
            'ETH': {'max_size': 10.0, 'max_notional': 30000},
            'default': {'max_size': 5.0, 'max_notional': 10000}
        },
        'volatility_thresholds': {
            'high': 0.05,
            'extreme': 0.1
        },
        'drawdown_limits': {
            'daily': 0.05,
            'weekly': 0.1,
            'monthly': 0.2
        },
        'exposure_limits': {
            'single_asset': 0.2,
            'asset_class': 0.4
        }
    },
    
    'collateral_thresholds': {
        'warning': 1.2,
        'critical': 1.1,
        'maintenance': 1.05,
        'liquidation': 1.025
    },
    
    'market_maker_params': {
        'spreads': {
            'BTC': {'min': 0.001, 'max': 0.005},
            'ETH': {'min': 0.002, 'max': 0.008},
            'default': {'min': 0.003, 'max': 0.01}
        },
        'inventory_limits': {
            'target': 0.0,
            'max_deviation': 0.2
        },
        'order_sizes': {
            'BTC': {'min': 0.001, 'max': 0.1},
            'ETH': {'min': 0.01, 'max': 1.0},
            'default': {'min': 0.1, 'max': 10.0}
        },
        'risk_params': {
            'max_position': 1.0,
            'max_leverage': 3.0,
            'min_profit': 0.001,
            'max_loss': 0.01
        }
    },
    
    'arbitrage': {
        'min_profit_threshold': 0.001,
        'max_position_size': 1.0,
        'execution_timeout': 30,
        'min_volume': 10000,
        'max_slippage': 0.002,
        'gas_threshold': 100,  # in gwei
        'pairs': ['BTC/USDT', 'ETH/USDT'],
        'exchanges': ['binance', 'coinbase', 'uniswap'],
        'defi_protocols': ['uniswap', 'sushiswap', 'curve']
    },
    
    'infrastructure': {
        'nodes': {
            'ethereum': {
                'primary': [
                    {
                        'url': ConfigurationManager.get_env_or_default('ETH_NODE_PRIMARY', 'https://mainnet.infura.io/v3/your-key'),
                        'chain': 'ethereum',
                        'type': 'primary',
                        'weight': 1.0,
                        'max_latency': 1.0,
                        'min_peers': 25
                    }
                ],
                'fallback': [
                    {
                        'url': ConfigurationManager.get_env_or_default('ETH_NODE_FALLBACK', 'https://eth-mainnet.alchemyapi.io/v2/your-key'),
                        'chain': 'ethereum',
                        'type': 'fallback',
                        'weight': 0.8,
                        'max_latency': 2.0,
                        'min_peers': 10
                    }
                ]
            },
            'polygon': {
                'primary': [
                    {
                        'url': ConfigurationManager.get_env_or_default('POLYGON_NODE_PRIMARY', 'https://polygon-rpc.com'),
                        'chain': 'polygon',
                        'type': 'primary',
                        'weight': 1.0,
                        'max_latency': 1.0,
                        'min_peers': 25
                    }
                ]
            }
        },
        'failover': {
            'check_interval': 60,
            'health_threshold': 0.7,
            'recovery_threshold': 0.85,
            'max_retry_attempts': 3,
            'retry_interval': 5
        }
    },
    
    'networks': {
        'ethereum': NetworkConfig(
            url=ConfigurationManager.get_env_or_default('ETH_NODE', 'https://mainnet.infura.io/v3/your-key'),
            chain_id=1,
            max_gas_price=300,
            confirmation_blocks=2,
            timeout=30
        ),
        'polygon': NetworkConfig(
            url=ConfigurationManager.get_env_or_default('POLYGON_NODE', 'https://polygon-rpc.com'),
            chain_id=137,
            max_gas_price=500,
            confirmation_blocks=5,
            timeout=60
        )
    },
    
    'defi': {
        'protocols': ['uniswap', 'sushiswap', 'curve', 'aave'],
        'max_slippage': 0.005,
        'min_liquidity': 100000,
        'gas_limit': 500000,
        'contracts': {
            'uniswap_v2_router': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',
            'uniswap_v3_router': '0xE592427A0AEce92De3Edee1F18E0157C05861564'
        }
    },
    
    'database': {
        'influxdb': {
            'url': ConfigurationManager.get_env_or_default('INFLUXDB_URL', 'http://localhost:8086'),
            'token': ConfigurationManager.get_env_or_default('INFLUXDB_TOKEN', 'your-token'),
            'org': ConfigurationManager.get_env_or_default('INFLUXDB_ORG', 'your-org'),
            'bucket': 'crypto_data'
        },
        'mongodb': {
            'url': ConfigurationManager.get_env_or_default('MONGODB_URL', 'mongodb://localhost:27017'),
            'database': 'crypto_db'
        },
        'redis': {
            'url': ConfigurationManager.get_env_or_default('REDIS_URL', 'redis://localhost:6379/0'),
            'password': ConfigurationManager.get_env_or_default('REDIS_PASSWORD', None)
        }
    },
    
    'monitoring': {
        'log_level': 'INFO',
        'metrics_interval': 60,
        'health_check_interval': 30,
        'alert_thresholds': {
            'error_rate': 0.01,
            'latency_ms': 1000,
            'memory_usage': 0.9
        }
    },
    
    'api': {
        'rate_limits': {
            'public': {'calls': 100, 'period': 60},
            'private': {'calls': 20, 'period': 60}
        },
        'timeout': 30,
        'retry': {
            'max_attempts': 3,
            'backoff_factor': 2
        }
    },
    
    'websocket': {
        'ping_interval': 30,
        'reconnect_delay': 5,
        'max_reconnects': 5
    },
    
    'system': {
        'main_loop_interval': 5,
        'cleanup_interval': 3600,
        'max_memory_usage': 0.8,
        'thread_pool_size': 4
    },
    
    'web3_provider': {
        'infura': 'https://mainnet.infura.io/v3/YOUR_ACTUAL_INFURA_PROJECT_ID',
        'alchemy': 'https://eth-mainnet.alchemyapi.io/v2/YOUR_ACTUAL_ALCHEMY_API_KEY'
    },
    'private_key': 'YOUR_ACTUAL_PRIVATE_KEY'
}

# Validation functions
def validate_config():
    """Validate configuration settings"""
    required_keys = [
        'exchange_credentials',
        'infrastructure',
        'database',
        'monitoring'
    ]
    
    for key in required_keys:
        if key not in CONFIG:
            raise ValueError(f"Missing required configuration key: {key}")
            
    # Validate exchange credentials
    for exchange in CONFIG['exchanges']:
        if exchange not in CONFIG['exchange_credentials']:
            raise ValueError(f"Missing credentials for exchange: {exchange}")
            
    # Validate network configurations
    for network in CONFIG['networks'].values():
        if not isinstance(network, NetworkConfig):
            raise ValueError("Invalid network configuration")

# Validate configuration on import
validate_config()