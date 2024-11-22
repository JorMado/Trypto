import asyncio
import logging
from typing import Dict, Optional

import aiohttp
from social_media_aggregator import SocialMediaAggregator
from news_analyzer import NewsAnalyzer
from sentiment_model import SentimentModel

logging.basicConfig(level=logging.INFO)

class CryptoSentimentAnalyzer:
    def __init__(self, api_keys: Optional[Dict[str, str]] = None, model_name="ProsusAI/finbert"):
        self.logger = logging.getLogger(__name__)
        self.api_keys = api_keys or {}
        self.model_name = model_name
        self.session = None
        try:
            self.model = self._load_sentiment_model()
        except Exception as e:
            self.logger.error(f"Failed to initialize sentiment analyzer: {str(e)}")
            # Initialize with None - system can still run without sentiment analysis
            self.model = None
        
    async def initialize(self):
        """Initialize sentiment analyzer connections"""
        self.session = aiohttp.ClientSession()
        return True
        
    async def analyze_sentiment(self, asset: str) -> float:
        """Analyze sentiment for given asset"""
        # Basic implementation - replace with actual sentiment analysis
        return self.sentiment_scores.get(asset, 0.0)
        
    async def get_market_sentiment(self, asset):
        data = await asyncio.gather(
            self.social_feeds.get_social_data(asset),
            self.news_analyzer.get_news_sentiment(asset)
        )
        
        return {
            'social_sentiment': self._analyze_social_sentiment(data[0]),
            'news_sentiment': data[1],
            'overall_score': self._calculate_combined_sentiment(data)
        }
        
    def _load_sentiment_model(self) -> SentimentModel:
        try:
            return SentimentModel(model_name=self.model_name)
        except Exception as e:
            self.logger.error(f"Could not load sentiment model: {str(e)}")
            return None

    def _analyze_social_sentiment(self, social_data: Dict) -> float:
        """Analyze sentiment from social media data"""
        if not social_data:
            return 0.0
        return self.model.predict(social_data)

    def _calculate_combined_sentiment(self, data) -> float:
        """Calculate combined sentiment score from all sources"""
        social_weight = 0.6
        news_weight = 0.4
        
        social_sentiment = self._analyze_social_sentiment(data[0])
        news_sentiment = data[1] if data[1] is not None else 0.0
        
        return (social_sentiment * social_weight) + (news_sentiment * news_weight)

    async def shutdown(self):
        """Cleanup any resources"""
        return True

    async def analyze(self, text):
        if self.model is None:
            self.logger.warning("Sentiment analysis unavailable - model not loaded")
            return 0.0  # neutral sentiment
        # ...existing code...

    async def cleanup_session(self):
        if self.session and not self.session.closed:
            try:
                await self.session.close()
            except Exception as e:
                self.logger.error(f"Error closing session: {e}")
            self.session = None