# gasOracle.py
import asyncio
import aiohttp
import time
from typing import Dict, Optional, List
import logging
from dataclasses import dataclass
import numpy as np
from web3 import Web3
import json
from datetime import datetime, timedelta

@dataclass
class GasInfo:
    safe_low: int
    standard: int
    fast: int
    instant: int
    base_fee: int
    priority_fee: int
    timestamp: datetime
    source: str
    network: str

class GasOracle:
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.logger = logging.getLogger(__name__)
        self.api_keys = api_keys or {
            'etherscan': '',
            'ethgasstation': '',
            'gasnow': ''
        }
        self.gas_prices = {
            'fast': 0,
            'standard': 0,
            'slow': 0
        }

    async def initialize(self):
        self.logger.info("Initializing GasOracle")
        return True

    async def update(self):
        # Basic implementation
        pass

    async def shutdown(self):
        self.logger.info("Shutting down GasOracle")

    def get_recommended_gas_price(self, priority: str = 'standard') -> int:
        return self.gas_prices.get(priority, self.gas_prices['standard'])
        
    async def close(self):
        """Close all connections"""
        if self.session:
            await self.session.close()
            
        # Close Web3 providers
        for provider in self.web3_providers.values():
            await provider.close()
            
    async def _initialize_web3_providers(self):
        """Initialize Web3 providers for each network"""
        provider_urls = {
            'ethereum': f"https://mainnet.infura.io/v3/{self.api_keys['infura']}",
            'polygon': f"https://polygon-mainnet.infura.io/v3/{self.api_keys['infura']}",
            'arbitrum': f"https://arbitrum-mainnet.infura.io/v3/{self.api_keys['infura']}",
            'optimism': f"https://optimism-mainnet.infura.io/v3/{self.api_keys['infura']}"
        }
        
        for network, url in provider_urls.items():
            self.web3_providers[network] = Web3(Web3.HTTPProvider(url))
            
    async def get_optimal_gas_price(self, network: str = 'ethereum') -> GasInfo:
        """
        Get optimal gas price with multiple data sources and prediction
        
        Args:
            network: Blockchain network to get gas price for
            
        Returns:
            GasInfo object containing current gas prices
        """
        if self._is_cache_valid(network):
            return self.cache[network]['data']
            
        try:
            # Gather gas prices from multiple sources
            gas_data = await asyncio.gather(
                self._get_gas_from_network(network),
                self._get_gas_from_etherscan(network),
                self._get_gas_from_blocknative(network),
                return_exceptions=True
            )
            
            # Filter out errors and aggregate data
            valid_data = [d for d in gas_data if not isinstance(d, Exception)]
            
            if not valid_data:
                raise Exception(f"Failed to get gas prices for {network}")
                
            # Combine and analyze gas prices
            gas_info = self._aggregate_gas_data(valid_data, network)
            
            # Update prediction models
            await self._update_gas_model(network, gas_info)
            
            # Cache the result
            self._update_cache(network, gas_info)
            
            return gas_info
            
        except Exception as e:
            logging.error(f"Error getting gas price for {network}: {str(e)}")
            raise
            
    async def _get_gas_from_network(self, network: str) -> Dict:
        """Get gas prices directly from the network"""
        web3 = self.web3_providers[network]
        
        try:
            # Get latest block
            block = await asyncio.to_thread(web3.eth.get_block, 'latest')
            
            # Get base fee and priority fee
            base_fee = block['baseFeePerGas']
            
            # Get priority fee suggestions
            priority_fee = await asyncio.to_thread(
                web3.eth.max_priority_fee,
            )
            
            return {
                'base_fee': base_fee,
                'priority_fee': priority_fee,
                'timestamp': datetime.now(),
                'source': 'network'
            }
            
        except Exception as e:
            logging.error(f"Error getting network gas price: {str(e)}")
            raise
            
    async def _get_gas_from_etherscan(self, network: str) -> Dict:
        """Get gas prices from Etherscan API"""
        if network != 'ethereum':
            raise ValueError("Etherscan only supports Ethereum network")
            
        try:
            async with self.session.get(
                'https://api.etherscan.io/api',
                params={
                    'module': 'gastracker',
                    'action': 'gasoracle',
                    'apikey': self.api_keys['etherscan']
                }
            ) as response:
                data = await response.json()
                
                if data['status'] != '1':
                    raise Exception(f"Etherscan API error: {data['message']}")
                    
                result = data['result']
                return {
                    'safe_low': int(result['SafeGasPrice']),
                    'standard': int(result['ProposeGasPrice']),
                    'fast': int(result['FastGasPrice']),
                    'timestamp': datetime.now(),
                    'source': 'etherscan'
                }
                
        except Exception as e:
            logging.error(f"Error getting Etherscan gas price: {str(e)}")
            raise
            
    async def _get_gas_from_blocknative(self, network: str) -> Dict:
        """Get gas prices from BlockNative API"""
        try:
            async with self.session.get(
                'https://api.blocknative.com/gasprices/blockprices',
                headers={
                    'Authorization': self.api_keys['blocknative']
                }
            ) as response:
                data = await response.json()
                
                return {
                    'safe_low': int(data['blockPrices'][0]['estimatedPrices'][3]['price']),
                    'standard': int(data['blockPrices'][0]['estimatedPrices'][2]['price']),
                    'fast': int(data['blockPrices'][0]['estimatedPrices'][1]['price']),
                    'instant': int(data['blockPrices'][0]['estimatedPrices'][0]['price']),
                    'timestamp': datetime.now(),
                    'source': 'blocknative'
                }
                
        except Exception as e:
            logging.error(f"Error getting BlockNative gas price: {str(e)}")
            raise
            
    def _aggregate_gas_data(self, gas_data: List[Dict], network: str) -> GasInfo:
        """Aggregate gas prices from multiple sources"""
        prices = {
            'safe_low': [],
            'standard': [],
            'fast': [],
            'instant': [],
            'base_fee': [],
            'priority_fee': []
        }
        
        # Collect all prices
        for data in gas_data:
            for key in prices.keys():
                if key in data:
                    prices[key].append(data[key])
                    
        # Calculate median values for each category
        aggregated = {}
        for key, values in prices.items():
            if values:
                aggregated[key] = int(np.median(values))
            else:
                aggregated[key] = 0
                
        return GasInfo(
            safe_low=aggregated['safe_low'],
            standard=aggregated['standard'],
            fast=aggregated['fast'],
            instant=aggregated['instant'],
            base_fee=aggregated['base_fee'],
            priority_fee=aggregated['priority_fee'],
            timestamp=datetime.now(),
            source='aggregated',
            network=network
        )
        
    async def predict_gas_price(self, network: str, 
                              time_horizon: int = 3600) -> Dict[str, float]:
        """
        Predict gas prices for the specified time horizon
        
        Args:
            network: Blockchain network
            time_horizon: Time horizon in seconds
            
        Returns:
            Dictionary with predicted gas prices
        """
        if network not in self.gas_price_models:
            await self._initialize_prediction_model(network)
            
        model = self.gas_price_models[network]
        historical_data = self.historical_data[network]
        
        # Generate prediction
        try:
            prediction = model.predict(historical_data, time_horizon)
            return {
                'predicted_base_fee': prediction['base_fee'],
                'predicted_priority_fee': prediction['priority_fee'],
                'confidence': prediction['confidence'],
                'time_horizon': time_horizon
            }
        except Exception as e:
            logging.error(f"Error predicting gas price: {str(e)}")
            return None
            
    async def _initialize_prediction_model(self, network: str):
        """Initialize gas price prediction model"""
        from sklearn.ensemble import RandomForestRegressor
        
        # Create and train model
        model = RandomForestRegressor(n_estimators=100)
        historical_data = await self._get_historical_gas_data(network)
        
        # Prepare features and target
        X, y = self._prepare_training_data(historical_data)
        
        # Train model
        await asyncio.to_thread(model.fit, X, y)
        
        self.gas_price_models[network] = model
        
    async def _get_historical_gas_data(self, network: str, 
                                     days: int = 7) -> List[Dict]:
        """Get historical gas price data"""
        try:
            async with self.session.get(
                f'https://api.etherscan.io/api',
                params={
                    'module': 'gastracker',
                    'action': 'gashistory',
                    'apikey': self.api_keys['etherscan'],
                    'days': days
                }
            ) as response:
                data = await response.json()
                return data['result']
        except Exception as e:
            logging.error(f"Error getting historical gas data: {str(e)}")
            return []
            
    def _is_cache_valid(self, network: str) -> bool:
        """Check if cached gas price is still valid"""
        if network not in self.cache:
            return False
            
        age = time.time() - self.cache[network]['timestamp']
        return age < self.cache_duration
        
    def _update_cache(self, network: str, gas_info: GasInfo):
        """Update gas price cache"""
        self.cache[network] = {
            'timestamp': time.time(),
            'data': gas_info
        }
        
    async def _load_historical_data(self):
        """Load historical gas price data for all networks"""
        for network in self.networks:
            self.historical_data[network] = await self._get_historical_gas_data(
                network
            )
            
    def get_recommended_gas_params(self, gas_info: GasInfo, 
                                 priority: str = 'standard') -> Dict:
        """
        Get recommended gas parameters for a transaction
        
        Args:
            gas_info: Current gas information
            priority: Transaction priority (safe_low, standard, fast, instant)
            
        Returns:
            Dictionary with recommended gas parameters
        """
        priority_multipliers = {
            'safe_low': 0.9,
            'standard': 1.0,
            'fast': 1.2,
            'instant': 1.5
        }
        
        multiplier = priority_multipliers.get(priority, 1.0)
        base_fee = gas_info.base_fee
        priority_fee = gas_info.priority_fee
        
        max_fee_per_gas = int(base_fee * multiplier * 1.25)  # 25% buffer
        max_priority_fee_per_gas = int(priority_fee * multiplier)
        
        return {
            'maxFeePerGas': max_fee_per_gas,
            'maxPriorityFeePerGas': max_priority_fee_per_gas,
            'type': '0x2',  # EIP-1559 transaction
            'estimated_cost': {
                'low': max_fee_per_gas * 21000,  # Basic transfer
                'high': max_fee_per_gas * 100000  # Complex contract interaction
            }
        }