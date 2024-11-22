# sentiment_model.py
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import List, Dict, Union
import numpy as np
import logging

from news_analyzer import NewsArticle
from social_media_aggregator import SocialPost

class SentimentModel:
    def __init__(self, model_name: str = 'ProsusAI/finbert'):
        self.logger = logging.getLogger(__name__)
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()
        except Exception as e:
            self.logger.error(f"Failed to load sentiment model: {str(e)}")
            # Fallback to a simpler model or raise the error depending on requirements
            raise
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        
    async def analyze_sentiment(self, texts: List[str]) -> List[Dict[str, float]]:
        """Analyze sentiment of multiple texts"""
        batches = self._create_batches(texts, batch_size=16)
        all_sentiments = []
        
        for batch in batches:
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='pt'
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                
            sentiments = self._process_outputs(outputs)
            all_sentiments.extend(sentiments)
            
        return all_sentiments
        
    def _create_batches(self, texts: List[str], batch_size: int) -> List[List[str]]:
        """Split texts into batches"""
        return [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        
    def _process_outputs(self, outputs) -> List[Dict[str, float]]:
        """Process model outputs into sentiment scores"""
        logits = outputs.logits
        probabilities = torch.softmax(logits, dim=1)
        
        sentiments = []
        for probs in probabilities:
            sentiment_dict = {
                'positive': float(probs[0]),
                'negative': float(probs[1]),
                'neutral': float(probs[2]),
                'composite_score': float(probs[0] - probs[1])
            }
            sentiments.append(sentiment_dict)
            
        return sentiments
        
    def analyze_social_post(self, post: SocialPost) -> Dict[str, float]:
        """Analyze sentiment of a social media post with context"""
        # Enhanced analysis considering social context
        base_sentiment = self.analyze_single_text(post.content)
        
        # Adjust sentiment based on engagement metrics
        engagement_factor = min(1.0, post.engagement_score / 10000)
        reliability_factor = post.source_reliability
        
        adjusted_sentiment = {
            'score': base_sentiment['composite_score'] * reliability_factor,
            'confidence': base_sentiment['confidence'] * engagement_factor,
            'impact': engagement_factor * reliability_factor
        }
        
        return adjusted_sentiment
        
    def analyze_news_article(self, article: NewsArticle) -> Dict[str, float]:
        """Analyze sentiment of a news article with context"""
        # Separate analysis for title and content
        title_sentiment = self.analyze_single_text(article.title)
        content_sentiment = self.analyze_single_text(article.content)
        
        # Weight title more heavily as it's often more impactful
        weighted_score = (
            title_sentiment['composite_score'] * 0.4 +
            content_sentiment['composite_score'] * 0.6
        )
        
        # Adjust based on source reliability and relevance
        reliability_factor = article.reliability_score
        relevance_factor = article.relevance_score
        
        return {
            'score': weighted_score * reliability_factor,
            'confidence': (title_sentiment['confidence'] + content_sentiment['confidence']) / 2,
            'impact': reliability_factor * relevance_factor
        }
        
    @staticmethod
    def _calculate_impact_score(engagement: float, followers: int) -> float:
        """Calculate impact score based on engagement and reach"""
        reach = np.log1p(followers)  # Log scale for follower count
        return (engagement * reach) / 100000  # Normalized score