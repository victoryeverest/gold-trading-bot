"""
News Sentiment Analyzer
Analyzes financial news for gold trading signals
Integrates with NewsAPI, Finnhub, Alpha Vantage
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

logger = logging.getLogger('trading')

# Try to import numpy
try:
    import numpy as np
except ImportError:
    np = None

# Import news fetcher
try:
    from news.fetcher import NewsAggregator, NewsArticle
    FETCHER_AVAILABLE = True
except ImportError:
    FETCHER_AVAILABLE = False
    logger.warning("News fetcher not available")


# Gold-specific keywords with sentiment weights
GOLD_KEYWORDS = {
    # Strong positive for gold
    'gold rally': 0.8,
    'gold surges': 0.8,
    'gold prices rise': 0.7,
    'safe haven demand': 0.7,
    'inflation hedge': 0.6,
    'central bank buying gold': 0.7,
    'geopolitical tension': 0.5,
    'us dollar weak': 0.6,
    'dollar weakness': 0.6,
    'fed rate cut': 0.7,
    'rate cuts expected': 0.6,
    'monetary easing': 0.6,
    'economic uncertainty': 0.5,
    'recession fears': 0.5,
    'investors seek safety': 0.5,
    'gold demand rises': 0.6,
    'bullish gold': 0.5,
    
    # Strong negative for gold
    'gold falls': -0.8,
    'gold drops': -0.8,
    'gold prices fall': -0.7,
    'risk appetite': -0.4,
    'risk-on sentiment': -0.4,
    'us dollar strong': -0.6,
    'dollar strength': -0.6,
    'fed rate hike': -0.7,
    'rate hike expected': -0.6,
    'tightening monetary': -0.6,
    'economic recovery': -0.4,
    'strong economy': -0.3,
    'stock market rally': -0.3,
    'bond yields rise': -0.5,
    'yields climb': -0.4,
    'bearish gold': -0.5,
    'gold selloff': -0.7,
    
    # Neutral/moderate keywords
    'xauusd': 0.0,
    'precious metals': 0.0,
    'comex': 0.0,
    'bullion': 0.0,
    'etf inflow': 0.4,
    'etf outflow': -0.4,
    'gold trading': 0.0,
    'gold futures': 0.0,
}

# High impact events that can cause volatility
HIGH_IMPACT_EVENTS = [
    'fomc', 'federal reserve', 'interest rate decision',
    'non-farm payrolls', 'nfp', 'cpi', 'inflation data',
    'gdp', 'retail sales', 'pmi', 'employment report',
    'fed chair speech', 'powell', 'ecb', 'bank of japan',
    'adp employment', 'ism', 'consumer confidence'
]


@dataclass
class NewsItem:
    title: str
    summary: str
    source: str
    timestamp: datetime
    sentiment: float
    impact: str  # 'HIGH', 'MEDIUM', 'LOW'
    relevance: float


class SentimentAnalyzer:
    """
    Analyzes news sentiment for trading signals.
    Uses keyword-based analysis with impact weighting.
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.news_config = config.get('TRADING_CONFIG', {})
        self.news_cache: List[NewsItem] = []
        self.last_sentiment = 0.0
        
        # Initialize news fetcher if available
        self.fetcher = None
        if FETCHER_AVAILABLE and self.news_config.get('NEWS_ENABLED', True):
            try:
                self.fetcher = NewsAggregator(config)
                logger.info("News aggregator initialized")
            except Exception as e:
                logger.warning(f"Could not initialize news fetcher: {e}")
    
    def analyze_text(self, text: str) -> Tuple[float, Dict]:
        """
        Analyze sentiment of text.
        Returns: (sentiment_score, keyword_matches)
        """
        if not text:
            return 0.0, {}
        
        text_lower = text.lower()
        total_sentiment = 0.0
        matches = {}
        
        for keyword, weight in GOLD_KEYWORDS.items():
            if keyword in text_lower:
                count = len(re.findall(re.escape(keyword), text_lower))
                total_sentiment += weight * count
                matches[keyword] = {'weight': weight, 'count': count}
        
        # Normalize to [-1, 1]
        if matches:
            max_possible = len(matches) * 2
            if np:
                normalized = np.clip(total_sentiment / max_possible, -1, 1)
            else:
                normalized = max(-1, min(1, total_sentiment / max_possible))
        else:
            normalized = 0.0
        
        return normalized, matches
    
    def check_high_impact(self, text: str) -> bool:
        """Check if text contains high-impact event keywords."""
        text_lower = text.lower()
        for event in HIGH_IMPACT_EVENTS:
            if event in text_lower:
                return True
        return False
    
    def _parse_timestamp(self, timestamp) -> datetime:
        """Parse timestamp to datetime."""
        if timestamp is None:
            return datetime.now()
        if isinstance(timestamp, datetime):
            return timestamp
        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return datetime.now()
        return datetime.now()
    
    def analyze_news(self, news_items: List[Dict]) -> float:
        """
        Analyze multiple news items and return aggregate sentiment.
        """
        if not news_items:
            return self.last_sentiment
        
        weighted_sentiment = 0.0
        total_weight = 0.0
        
        for item in news_items:
            title = item.get('title', '')
            summary = item.get('summary', '')
            source = item.get('source', 'unknown')
            timestamp = self._parse_timestamp(item.get('timestamp'))
            
            # Analyze title and summary
            title_sentiment, _ = self.analyze_text(title)
            summary_sentiment, _ = self.analyze_text(summary)
            
            # Combined sentiment (title weighted higher)
            combined = title_sentiment * 0.6 + summary_sentiment * 0.4
            
            # Impact weighting
            is_high_impact = self.check_high_impact(title + ' ' + summary)
            impact_weight = 2.0 if is_high_impact else 1.0
            
            # Recency weighting
            age_hours = (datetime.now() - timestamp).total_seconds() / 3600
            recency_weight = max(0.1, 1.0 - (age_hours / 24))
            
            # Source reliability weighting
            source_weight = self.get_source_weight(source)
            
            # Total weight
            weight = impact_weight * recency_weight * source_weight
            
            weighted_sentiment += combined * weight
            total_weight += weight
            
            # Store in cache
            news_item = NewsItem(
                title=title,
                summary=summary,
                source=source,
                timestamp=timestamp,
                sentiment=combined,
                impact='HIGH' if is_high_impact else 'MEDIUM',
                relevance=recency_weight
            )
            self.news_cache.append(news_item)
        
        # Calculate aggregate sentiment
        if total_weight > 0:
            aggregate_sentiment = weighted_sentiment / total_weight
        else:
            aggregate_sentiment = 0.0
        
        # Apply smoothing
        smoothed = 0.7 * self.last_sentiment + 0.3 * aggregate_sentiment
        self.last_sentiment = smoothed
        
        # Clean old cache
        self._clean_cache()
        
        return smoothed
    
    def get_source_weight(self, source: str) -> float:
        """Get reliability weight for news source."""
        high_reliability = [
            'reuters', 'bloomberg', 'financial times', 'wsj', 'cnbc',
            'marketwatch', 'investing.com', 'fxstreet'
        ]
        source_lower = source.lower()
        
        for reliable in high_reliability:
            if reliable in source_lower:
                return 1.2
        
        return 1.0
    
    def _clean_cache(self):
        """Remove old news items from cache."""
        cutoff = datetime.now() - timedelta(hours=48)
        self.news_cache = [item for item in self.news_cache if item.timestamp > cutoff]
    
    def get_trading_signal(self, sentiment: float) -> Dict:
        """Convert sentiment to trading signal."""
        signal = {
            'action': 'NEUTRAL',
            'confidence': 0.0,
            'reason': ''
        }
        
        if sentiment > 0.3:
            signal['action'] = 'BULLISH'
            signal['confidence'] = min(sentiment, 1.0)
            signal['reason'] = f'Positive gold sentiment ({sentiment:.2f})'
        elif sentiment < -0.3:
            signal['action'] = 'BEARISH'
            signal['confidence'] = min(abs(sentiment), 1.0)
            signal['reason'] = f'Negative gold sentiment ({sentiment:.2f})'
        else:
            signal['action'] = 'NEUTRAL'
            signal['confidence'] = 1.0 - abs(sentiment)
            signal['reason'] = 'Neutral sentiment'
        
        return signal
    
    def check_news_blackout(self, minutes: int = 15) -> Tuple[bool, str]:
        """Check if we should avoid trading due to upcoming news."""
        now = datetime.now()
        
        for item in self.news_cache:
            if item.impact == 'HIGH':
                time_diff = (item.timestamp - now).total_seconds() / 60
                if abs(time_diff) < minutes:
                    return True, f'High impact news: {item.title}'
        
        return False, ''
    
    def get_recent_headlines(self, count: int = 5) -> List[str]:
        """Get recent news headlines for display."""
        recent = sorted(self.news_cache, key=lambda x: x.timestamp, reverse=True)
        return [f"[{item.impact}] {item.title}" for item in recent[:count]]
    
    async def fetch_latest_news(self) -> List[Dict]:
        """Fetch latest news from configured sources."""
        if self.fetcher:
            try:
                articles = await self.fetcher.fetch_all_news(hours=24)
                return [
                    {
                        'title': a.title,
                        'summary': a.description,
                        'source': a.source,
                        'timestamp': a.published_at
                    }
                    for a in articles
                ]
            except Exception as e:
                logger.error(f"Error fetching news: {e}")
        return []


class EconomicCalendar:
    """Economic calendar integration for scheduled events."""
    
    def __init__(self):
        self.events = []
    
    def add_event(self, event: Dict):
        """Add scheduled economic event."""
        self.events.append(event)
    
    def get_upcoming_events(self, hours: int = 24) -> List[Dict]:
        """Get events in the next N hours."""
        now = datetime.now()
        upcoming = []
        
        for event in self.events:
            event_time = event.get('datetime')
            if event_time:
                if isinstance(event_time, str):
                    event_time = datetime.fromisoformat(event_time)
                
                time_until = (event_time - now).total_seconds() / 3600
                if 0 <= time_until <= hours:
                    upcoming.append(event)
        
        return sorted(upcoming, key=lambda x: x.get('datetime', now))


# Convenience function
async def get_current_sentiment(config: Dict) -> float:
    """Get current gold market sentiment."""
    analyzer = SentimentAnalyzer(config)
    news = await analyzer.fetch_latest_news()
    return analyzer.analyze_news(news)