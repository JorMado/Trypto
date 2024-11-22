import numpy as np
from typing import Dict, List, Optional

class VolatilityCalculator:
    def __init__(self):
        self.volatility_cache: Dict[str, float] = {}
        self.price_history: Dict[str, List[float]] = {}
        
    def get_volatility(self, asset: str) -> float:
        """Returns the volatility for a given asset"""
        if asset in self.volatility_cache:
            return self.volatility_cache[asset]
        return 0.0  # Default value if no data available
        
    def update_prices(self, asset: str, price: float):
        """Updates price history for volatility calculation"""
        if asset not in self.price_history:
            self.price_history[asset] = []
        self.price_history[asset].append(price)
        self._calculate_volatility(asset)
        
    def _calculate_volatility(self, asset: str):
        """Calculates historical volatility for an asset"""
        if asset not in self.price_history:
            return
            
        prices = self.price_history[asset][-30:]  # Use last 30 prices
        if len(prices) < 2:
            return
            
        returns = np.diff(np.log(prices))
        volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
        self.volatility_cache[asset] = volatility
