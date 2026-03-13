"""
News Fetcher Module
Fetches real-time financial news from multiple sources
Supports: NewsAPI, Finnhub, Alpha Vantage, Web Scraping
"""

import os
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import re

logger = logging.getLogger('trading')


@dataclass
class NewsArticle:
    title: str
    description: str
    source: str
    url: str
    published_at: datetime
    sentiment: float = 0.0


class NewsAPIFetcher:
    """
    NewsAPI.org - Free tier: 100 requests/day
    Good for general financial news
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('NEWS_API_KEY', '')
        self.base_url = 'https://newsapi.org/v2'
        
    async def fetch_gold_news(self, hours: int = 24) -> List[NewsArticle]:
        """Fetch gold-related news articles."""
        if not self.api_key:
            logger.warning("NewsAPI key not configured")
            return []
        
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(hours=hours)
        
        # Search queries for gold news
        queries = [
            'gold price',
            'XAUUSD',
            'gold market',
            'precious metals',
            'Federal Reserve gold'
        ]
        
        articles = []
        
        async with aiohttp.ClientSession() as session:
            for query in queries[:2]:  # Limit to avoid rate limits
                try:
                    url = f"{self.base_url}/everything"
                    params = {
                        'q': query,
                        'from': from_date.isoformat(),
                        'to': to_date.isoformat(),
                        'sortBy': 'publishedAt',
                        'language': 'en',
                        'pageSize': 10,
                        'apiKey': self.api_key
                    }
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            for article in data.get('articles', []):
                                articles.append(NewsArticle(
                                    title=article.get('title', ''),
                                    description=article.get('description', ''),
                                    source=article.get('source', {}).get('name', 'unknown'),
                                    url=article.get('url', ''),
                                    published_at=datetime.fromisoformat(
                                        article.get('publishedAt', '').replace('Z', '+00:00')
                                    ) if article.get('publishedAt') else datetime.now()
                                ))
                        else:
                            logger.error(f"NewsAPI error: {response.status}")
                            
                except Exception as e:
                    logger.error(f"Error fetching news: {e}")
                    
                await asyncio.sleep(0.5)  # Rate limiting
        
        return articles


class FinnhubFetcher:
    """
    Finnhub.io - Free tier: 60 calls/minute
    Good for market news and company specific
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('FINNHUB_API_KEY', '')
        self.base_url = 'https://finnhub.io/api/v1'
        
    async def fetch_market_news(self, category: str = 'forex') -> List[NewsArticle]:
        """Fetch market news from Finnhub."""
        if not self.api_key:
            logger.warning("Finnhub API key not configured")
            return []
        
        articles = []
        
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/news"
                params = {
                    'category': category,
                    'token': self.api_key
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for article in data[:20]:
                            articles.append(NewsArticle(
                                title=article.get('headline', ''),
                                description=article.get('summary', ''),
                                source=article.get('source', 'unknown'),
                                url=article.get('url', ''),
                                published_at=datetime.fromtimestamp(
                                    article.get('datetime', 0)
                                ) if article.get('datetime') else datetime.now()
                            ))
                    else:
                        logger.error(f"Finnhub error: {response.status}")
                        
            except Exception as e:
                logger.error(f"Error fetching from Finnhub: {e}")
        
        return articles


class AlphaVantageFetcher:
    """
    Alpha Vantage - Free tier: 25 calls/day
    Good for sentiment analysis
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('ALPHA_VANTAGE_API_KEY', '')
        self.base_url = 'https://www.alphavantage.co/query'
        
    async def fetch_sentiment(self) -> Dict:
        """Fetch market sentiment from Alpha Vantage."""
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured")
            return {}
        
        async with aiohttp.ClientSession() as session:
            try:
                params = {
                    'function': 'NEWS_SENTIMENT',
                    'tickers': 'XAU',
                    'apikey': self.api_key
                }
                
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('feed', [])
                        
            except Exception as e:
                logger.error(f"Error fetching from Alpha Vantage: {e}")
        
        return {}


class InvestingComScraper:
    """
    Scrapes Investing.com for gold news (no API key needed)
    Free but requires more maintenance
    """
    
    def __init__(self):
        self.urls = [
            'https://www.investing.com/news/commodities-news',
            'https://www.investing.com/news/forex-news'
        ]
        
    async def fetch_news(self) -> List[NewsArticle]:
        """Scrape investing.com for gold news."""
        articles = []
        
        async with aiohttp.ClientSession() as session:
            for url in self.urls:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            html = await response.text()
                            
                            # Parse articles (simplified)
                            # In production, use BeautifulSoup
                            title_pattern = r'<a[^>]*class="title[^"]*"[^>]*>([^<]+)</a>'
                            titles = re.findall(title_pattern, html)
                            
                            for title in titles[:10]:
                                if 'gold' in title.lower() or 'xau' in title.lower():
                                    articles.append(NewsArticle(
                                        title=title.strip(),
                                        description='',
                                        source='investing.com',
                                        url='',
                                        published_at=datetime.now()
                                    ))
                                    
                except Exception as e:
                    logger.error(f"Error scraping: {e}")
                    
                await asyncio.sleep(1)
        
        return articles


class NewsAggregator:
    """
    Aggregates news from multiple sources.
    Falls back gracefully if APIs not configured.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Initialize fetchers
        self.newsapi = NewsAPIFetcher(
            api_key=os.environ.get('NEWS_API_KEY', '')
        )
        self.finnhub = FinnhubFetcher(
            api_key=os.environ.get('FINNHUB_API_KEY', '')
        )
        self.alphavantage = AlphaVantageFetcher(
            api_key=os.environ.get('ALPHA_VANTAGE_API_KEY', '')
        )
        self.scraper = InvestingComScraper()
        
    async def fetch_all_news(self, hours: int = 24) -> List[NewsArticle]:
        """Fetch news from all available sources."""
        all_articles = []
        
        # Try each source
        tasks = [
            self.newsapi.fetch_gold_news(hours),
            self.finnhub.fetch_market_news('forex'),
            # self.scraper.fetch_news(),  # Enable if needed
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"News fetch error: {result}")
        
        # Deduplicate by title
        seen_titles = set()
        unique_articles = []
        
        for article in all_articles:
            title_lower = article.title.lower()
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_articles.append(article)
        
        # Sort by date
        unique_articles.sort(key=lambda x: x.published_at, reverse=True)
        
        logger.info(f"Fetched {len(unique_articles)} unique articles")
        return unique_articles
    
    def get_news_for_trading(self) -> List[Dict]:
        """Synchronous wrapper for trading engine."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            articles = loop.run_until_complete(self.fetch_all_news())
            return [
                {
                    'title': a.title,
                    'summary': a.description,
                    'source': a.source,
                    'timestamp': a.published_at
                }
                for a in articles
            ]
        finally:
            loop.close()


# Free API Keys Setup Guide
SETUP_GUIDE = """
📰 NEWS API SETUP GUIDE
======================

1. NEWSAPI (Recommended - Free 100 requests/day)
   • Go to: https://newsapi.org/register
   • Register and get your API key
   • Set: export NEWS_API_KEY=your_key_here

2. FINNHUB (Free 60 calls/minute)
   • Go to: https://finnhub.io/register
   • Get your free API key
   • Set: export FINNHUB_API_KEY=your_key_here

3. ALPHA VANTAGE (Free 25 calls/day)
   • Go to: https://www.alphavantage.co/support/#api-key
   • Get free API key
   • Set: export ALPHA_VANTAGE_API_KEY=your_key_here

For basic usage, just NewsAPI is sufficient.
The bot will work without any API keys (keyword analysis only).
"""


if __name__ == "__main__":
    print(SETUP_GUIDE)