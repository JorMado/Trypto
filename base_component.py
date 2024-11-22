
import logging
from abc import ABC

class BaseComponent(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
    async def initialize(self):
        """Initialize the component"""
        return True
        
    async def shutdown(self):
        """Cleanup resources"""
        return True

    async def check(self):
        """Health check"""
        return True