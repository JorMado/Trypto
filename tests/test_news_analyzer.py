import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from src.trypto.news_analyzer import NewsAnalyzer

@pytest.fixture
def mock_news_data():
    return [
        {'title': 'Bitcoin hits new high', 'content': '...'},
        {'title': 'Market crashes', 'content': '...'}
    ]

def test_sentiment_analysis(mock_news_data):
    news_analyzer = NewsAnalyzer(api_keys={})
    sentiments = news_analyzer.analyze_news(mock_news_data)
    # Verify sentiments are correctly calculated
    assert isinstance(sentiments, list)
    assert len(sentiments) == len(mock_news_data)
    for sentiment in sentiments:
        assert 'title' in sentiment
        assert 'sentiment_score' in sentiment
        assert -1.0 <= sentiment['sentiment_score'] <= 1.0