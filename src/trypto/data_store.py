# data_store.py
import asyncio
import redis.asyncio as aioredis
import motor.motor_asyncio
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
from typing import Dict, Optional, List, Any
import logging
from datetime import datetime, timedelta

class CryptoDataStore:
    def __init__(self, config: Dict[str, Dict]):
        """
        Initialize data storage systems
        
        Args:
            config: Configuration dictionary containing settings for each database
        """
        # Initialize InfluxDB client
        self.influx_client = InfluxDBClient(
            url=config['influxdb']['url'],
            token=config['influxdb']['token'],
            org=config['influxdb']['org']
        )
        self.influx_write_api = self.influx_client.write_api(
            write_options=WriteOptions(
                batch_size=500,
                flush_interval=10_000,
                jitter_interval=2_000,
                retry_interval=5_000,
                max_retries=5,
                max_retry_delay=30_000,
                exponential_base=2
            )
        )
        self.influx_bucket = config['influxdb']['bucket']
        
        # Initialize MongoDB client
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(
            config['mongodb']['url']
        )
        self.mongo_db = self.mongo_client[config['mongodb']['database']]
        
        # Initialize Redis client
        self.redis = aioredis.Redis.from_url(
            config['redis']['url'],
            encoding='utf-8',
            decode_responses=True
        )
        
        # Setup logging
        self.logger = logging.getLogger('CryptoDataStore')
        self.logger.setLevel(logging.INFO)
        
    async def close(self):
        """Close all database connections"""
        self.influx_client.close()
        self.mongo_client.close()
        await self.redis.close()
        
    async def store_market_data(self, data: Dict):
        """
        Store market data in InfluxDB
        
        Args:
            data: Market data dictionary containing price, volume, etc.
        """
        try:
            point = (Point("market_data")
                    .tag("exchange", data['exchange'])
                    .tag("pair", data['pair'])
                    .field("price", float(data['price']))
                    .field("volume", float(data['volume']))
                    .field("liquidity", float(data['liquidity']))
                    .time(datetime.utcnow()))
            
            self.influx_write_api.write(
                bucket=self.influx_bucket,
                record=point
            )
            
        except Exception as e:
            self.logger.error(f"Error storing market data: {str(e)}")
            raise
            
    async def store_blockchain_data(self, collection: str, data: Dict):
        """
        Store blockchain data in MongoDB
        
        Args:
            collection: Name of the MongoDB collection
            data: Blockchain data to store
        """
        try:
            await self.mongo_db[collection].insert_one(data)
        except Exception as e:
            self.logger.error(f"Error storing blockchain data: {str(e)}")
            raise
            
    async def cache_data(self, key: str, value: Any, expire: Optional[int] = None):
        """
        Cache data in Redis
        
        Args:
            key: Redis key
            value: Value to cache
            expire: Optional expiration time in seconds
        """
        try:
            await self.redis.set(key, value, ex=expire)
        except Exception as e:
            self.logger.error(f"Error caching data: {str(e)}")
            raise
            
    async def get_cached_data(self, key: str) -> Optional[str]:
        """
        Retrieve cached data from Redis
        
        Args:
            key: Redis key
            
        Returns:
            Cached value or None if not found
        """
        try:
            return await self.redis.get(key)
        except Exception as e:
            self.logger.error(f"Error retrieving cached data: {str(e)}")
            return None
            
    async def query_market_data(
        self,
        exchange: str,
        pair: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = '1m'
    ) -> List[Dict]:
        """
        Query market data from InfluxDB
        
        Args:
            exchange: Exchange name
            pair: Trading pair
            start_time: Start time for query
            end_time: Optional end time for query
            interval: Time interval for aggregation
            
        Returns:
            List of market data points
        """
        try:
            query = f'''
                from(bucket: "{self.influx_bucket}")
                    |> range(start: {start_time.isoformat()}Z
                           {f', stop: {end_time.isoformat()}Z' if end_time else ''})
                    |> filter(fn: (r) => r["exchange"] == "{exchange}")
                    |> filter(fn: (r) => r["pair"] == "{pair}")
                    |> aggregateWindow(every: {interval}, fn: mean)
                    |> yield(name: "mean")
            '''
            
            result = []
            query_api = self.influx_client.query_api()
            tables = query_api.query(query)
            
            for table in tables:
                for record in table.records:
                    result.append({
                        'timestamp': record.get_time(),
                        'price': record.get_value(),
                        'volume': record.values.get('volume'),
                        'liquidity': record.values.get('liquidity')
                    })
                    
            return result
            
        except Exception as e:
            self.logger.error(f"Error querying market data: {str(e)}")
            raise
            
    async def aggregate_blockchain_data(
        self,
        collection: str,
        pipeline: List[Dict]
    ) -> List[Dict]:
        """
        Aggregate blockchain data from MongoDB
        
        Args:
            collection: MongoDB collection name
            pipeline: Aggregation pipeline
            
        Returns:
            Aggregation results
        """
        try:
            return await self.mongo_db[collection].aggregate(pipeline).to_list(None)
        except Exception as e:
            self.logger.error(f"Error aggregating blockchain data: {str(e)}")
            raise
            
    async def cleanup_old_data(self, days: int = 30):
        """
        Clean up old data from databases
        
        Args:
            days: Number of days of data to keep
        """
        try:
            # Delete old InfluxDB data
            delete_api = self.influx_client.delete_api()
            start = datetime.min
            stop = datetime.now() - timedelta(days=days)
            
            delete_api.delete(
                start,
                stop,
                f'_measurement="market_data"',
                bucket=self.influx_bucket
            )
            
            # Delete old MongoDB data
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            for collection in await self.mongo_db.list_collection_names():
                await self.mongo_db[collection].delete_many({
                    'timestamp': {'$lt': cutoff_date}
                })
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {str(e)}")
            raise
            
    async def backup_data(self, backup_path: str):
        """
        Backup data to specified path
        
        Args:
            backup_path: Path to store backups
        """
        try:
            # Backup MongoDB
            await self.mongo_client.admin.command('fsync', lock=False)
            # Implement backup logic here
            
            # Backup InfluxDB
            # Implement backup logic here
            
        except Exception as e:
            self.logger.error(f"Error backing up data: {str(e)}")
            raise

# Example configuration
DATA_STORE_CONFIG = {
    'influxdb': {
        'url': 'http://localhost:8086',
        'token': 'your-token',
        'org': 'your-org',
        'bucket': 'crypto_data'
    },
    'mongodb': {
        'url': 'mongodb://localhost:27017',
        'database': 'crypto_db'
    },
    'redis': {
        'url': 'redis://localhost:6379'
    }
}