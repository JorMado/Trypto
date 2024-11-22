import logging
from abc import ABC

class BaseComponent:
    def __init__(self):
        pass
        
    async def initialize(self):
        """Initialize the component"""
        return True
        
    async def shutdown(self):
        """Cleanup resources"""
        return True

    async def check(self):
        """Health check"""
        return True