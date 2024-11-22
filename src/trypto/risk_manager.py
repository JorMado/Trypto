import logging
from typing import Dict, List, Optional
from datetime import datetime
from trypto.blockchain_monitor import BlockchainMonitor
from trypto.volatility_calculator import VolatilityCalculator

class CryptoRiskManager:
    def __init__(self, risk_params: Dict):
        self.logger = logging.getLogger(__name__)
        self.risk_params = risk_params
        self.blockchain_monitor = BlockchainMonitor()
        self.volatility_calculator = VolatilityCalculator()
        self.health_metrics = {
            'total_positions': 0,
            'risk_exposure': 0.0,
            'margin_usage': 0.0,
            'last_check': None,
            'alerts': [],
            'status': 'healthy'
        }
        self.positions = {}  # Track current positions
        self.position_updates = []  # Track position changes
        
    async def initialize(self):
        await self.blockchain_monitor.initialize()
        self.logger.info("Risk manager initialized")
        return True
        
    async def monitor(self):
        metrics = await self.blockchain_monitor.update_metrics()
        network_status = await self.blockchain_monitor.get_network_status()
        # Add risk monitoring logic here
        try:
            # Update health metrics during regular risk monitoring
            positions = await self._get_current_positions()
            self.health_metrics.update({
                'total_positions': len(positions),
                'risk_exposure': self._calculate_risk_exposure(positions),
                'margin_usage': self._calculate_margin_usage(positions),
                'last_check': datetime.now(),
                'status': 'healthy'
            })
        except Exception as e:
            self.health_metrics['status'] = 'error'
            self.health_metrics['alerts'].append(str(e))
            raise
        return True
        
    async def shutdown(self):
        await self.blockchain_monitor.shutdown()
        return True

    async def calculate_position_risk(self, portfolio):
        risk_metrics = {}
        
        for asset, position in portfolio.items():
            volatility = self.volatility_calculator.get_volatility(asset)
            network_risk = await self.blockchain_monitor.get_network_risk(asset)
            
            risk_metrics[asset] = {
                'var': self._calculate_crypto_var(position, volatility),
                'network_risk_score': network_risk,
                'liquidation_risk': self._calculate_liquidation_risk(position),
                'smart_contract_risk': await self._assess_smart_contract_risk(asset)
            }
            
        return risk_metrics

    async def get_health(self) -> dict:
        """Return current health metrics of the risk manager"""
        return {
            'metrics': self.health_metrics,
            'risk_params': self.risk_params,
            'status': self.health_metrics['status']
        }

    async def _get_current_positions(self) -> Dict:
        """Get current positions across all trading pairs"""
        try:
            # In mock mode, return empty positions
            return self.positions
        except Exception as e:
            self.health_metrics['alerts'].append(f"Position fetch error: {str(e)}")
            return {}

    def _calculate_risk_exposure(self, positions: Dict) -> float:
        """Calculate total risk exposure from positions"""
        try:
            total_exposure = sum(
                abs(pos['size'] * pos.get('price', 0)) 
                for pos in positions.values()
            )
            return total_exposure
        except Exception:
            return 0.0

    def _calculate_margin_usage(self, positions: Dict) -> float:
        """Calculate current margin usage percentage"""
        try:
            used_margin = sum(
                pos.get('margin_used', 0) 
                for pos in positions.values()
            )
            total_margin = self.risk_params.get('total_margin', 100000)
            return (used_margin / total_margin) if total_margin else 0.0
        except Exception:
            return 0.0