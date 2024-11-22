import logging
import websockets
import asyncio
from typing import Dict
import json
import time

class WSFeedHandler:
    def __init__(self, websocket: str, exchange_id: str, mock_mode: bool = True):
        self.logger = logging.getLogger(__name__)
        self.websocket_url = websocket
        self.exchange_id = exchange_id
        self.ws = None
        self.running = False
        self.connected = False
        self.retry_delay = 5
        self.mock_mode = mock_mode
        self.mock_data = {
            'BTC/USDT': {'price': 50000, 'volume': 1.5},
            'ETH/USDT': {'price': 3000, 'volume': 10},
            'SOL/USDT': {'price': 100, 'volume': 50}
        }
        self.exchange_configs = {
            'binance': {
                'url': 'wss://stream.binance.com:9443/ws',
                'headers': {
                    'User-Agent': 'TryptoBot/1.0',
                    'Accept': 'application/json'
                },
                'ping_interval': 20,
                'ping_timeout': 20
            },
            'coinbase': {
                'url': 'wss://ws-feed.pro.coinbase.com',
                'headers': {
                    'User-Agent': 'TryptoBot/1.0',
                    'Accept': 'application/json'
                },
                'ping_interval': 30,
                'ping_timeout': 30
            },
            'kraken': {
                'url': 'wss://ws.kraken.com',
                'headers': {
                    'User-Agent': 'TryptoBot/1.0',
                    'Origin': 'https://www.kraken.com'
                },
                'ping_interval': 30,
                'ping_timeout': 30
            },
            'ftx': {
                'url': 'wss://ftx.com/ws/',
                'headers': {
                    'User-Agent': 'TryptoBot/1.0',
                    'Accept': 'application/json',
                    'FTX-KEY': 'YOUR_API_KEY',  # Replace in production
                    'FTX-SIGN': 'YOUR_SIGNATURE'  # Replace in production
                },
                'ping_interval': 15,
                'ping_timeout': 15
            }
        }

    async def initialize(self):
        """Initialize websocket connection"""
        await self.connect()

    async def connect(self):
        if self.mock_mode:
            self.connected = True
            self.logger.info("Connected to mock websocket feed")
            return

        try:
            config = self.exchange_configs.get(self.exchange_id)
            if not config:
                raise ValueError(f"Unsupported exchange: {self.exchange_id}")

            self.ws = await websockets.connect(
                config['url'],
                ping_interval=config['ping_interval'],
                ping_timeout=config['ping_timeout'],
                extra_headers=config['headers']
            )
            self.connected = True
            self.logger.info(f"Connected to {self.exchange_id} websocket")
            
            if self.exchange_id == 'ftx':
                await self._authenticate_ftx()
            elif self.exchange_id == 'kraken':
                await self._authenticate_kraken()
            # Add other exchange-specific authentication as needed

        except Exception as e:
            self.logger.error(f"Failed to connect to {self.exchange_id}: {str(e)}")
            self.connected = False
            await asyncio.sleep(self.retry_delay)

    async def _authenticate_ftx(self):
        """FTX specific authentication"""
        if self.ws and self.connected:
            auth_msg = {
                "op": "login",
                "args": {
                    "key": "YOUR_API_KEY",  # Replace in production
                    "sign": "YOUR_SIGNATURE",  # Replace in production
                    "time": int(time.time() * 1000)
                }
            }
            await self.ws.send(json.dumps(auth_msg))

    async def _authenticate_kraken(self):
        """Kraken specific authentication"""
        if self.ws and self.connected:
            auth_msg = {
                "event": "subscribe",
                "subscription": {
                    "name": "ownTrades",
                    "token": "YOUR_TOKEN"  # Replace in production
                }
            }
            await self.ws.send(json.dumps(auth_msg))

    async def process(self):
        if self.mock_mode:
            await asyncio.sleep(0.5)  # Longer sleep in mock mode
            # Return mock data without simulating failure
            mock_response = {
                'status': 'ok',
                'data': self.mock_data,
                'timestamp': time.time()
            }
            return mock_response

        if not self.ws:
            return
        
        try:
            message = await self.ws.recv()
            # Process message here
            return message
        except Exception as e:
            self.logger.error(f"Error processing websocket message: {str(e)}")

    async def cleanup_session(self):
        """Cleanup websocket session"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception as e:
                self.logger.error(f"Error closing websocket session: {e}")
            self.session = None

    async def shutdown(self):
        await self.cleanup_session()
        # Additional cleanup...