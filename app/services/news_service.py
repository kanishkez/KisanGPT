import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(hours=2)  # Cache for 2 hours
        self.news_sources = [
            "https://krishijagran.com/feed/",
            "https://www.pib.gov.in/rssFeed.aspx?langid=2",
            "https://icar.org.in/rss-feed"
        ]
        
    async def get_pesticide_news(self) -> Dict[str, Any]:
        """Get pesticide related news and updates"""
        try:
            # Reuse agricultural news but filter for pesticide content
            news = await self.get_agricultural_news(limit=10)
            if "error" in news:
                return news
                
            # Filter news items related to pesticides or pest control
            pesticide_keywords = ['pesticide', 'pest', 'insecticide', 'disease', 'protection']
            filtered_items = []
            for item in news.get('items', news.get('news', [])):
                title = item.get('title', '')
                content = item.get('content', item.get('description', ''))
                if any(keyword in title.lower() or keyword in content.lower() 
                      for keyword in pesticide_keywords):
                    filtered_items.append(item)
            
            return {
                'items': filtered_items[:5],
                'summary': f"Found {len(filtered_items)} pesticide-related updates"
            }
            
        except Exception as e:
            logger.error(f"Error getting pesticide news: {str(e)}")
            return {
                "error": str(e),
                "items": [],
                "summary": "Pesticide news unavailable"
            }

    async def get_agricultural_news(self, limit: int = 5) -> Dict[str, Any]:
        """Get latest agricultural news"""
        try:
            cache_key = f"news_{limit}"
            
            # Check cache first
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    logger.info("Returning cached news data")
                    return cached_data['data']

            # Get news from RSS feeds or mock data
            news = await self._fetch_news(limit)
            
            # Cache the result
            self.cache[cache_key] = {
                'data': news,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Retrieved {len(news.get('news', []))} news items")
            return news
            
        except Exception as e:
            logger.error(f"Error getting agricultural news: {str(e)}")
            return {
                "error": str(e),
                "news": [],
                "summary": "News unavailable"
            }

    async def _fetch_news(self, limit: int = 5) -> Dict[str, Any]:
        """Fetch news from RSS feeds or return mock data"""
        try:
            # For now, return mock data. In production, integrate with real RSS feeds
            mock_news = self._get_mock_news()
            
            return {
                "items": mock_news[:limit],
                "news": mock_news[:limit],  # Keep both for compatibility
                "summary": self._format_news_summary(mock_news[:limit]),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}")
            return {"news": [], "summary": "News unavailable"}

    def _get_mock_news(self) -> List[Dict[str, Any]]:
        """Get mock agricultural news data"""
        return [
            {
                "title": "नई कीटनाशक नीति जारी - किसानों के लिए राहत",
                "content": "सरकार ने नई कीटनाशक नीति जारी की है जो किसानों को बेहतर सुरक्षा प्रदान करेगी।",
                "source": "Krishi Jagran",
                "published_at": datetime.now() - timedelta(hours=2),
                "url": "https://krishijagran.com/news1"
            },
            {
                "title": "मौसम विभाग ने बारिश का पूर्वानुमान जारी किया",
                "content": "अगले सप्ताह देश के कई हिस्सों में बारिश की संभावना है।",
                "source": "PIB",
                "published_at": datetime.now() - timedelta(hours=4),
                "url": "https://pib.gov.in/news2"
            },
            {
                "title": "गेहूं की नई किस्म विकसित - उत्पादन में 20% वृद्धि",
                "content": "ICAR ने गेहूं की नई किस्म विकसित की है जो उत्पादन में 20% वृद्धि करेगी।",
                "source": "ICAR",
                "published_at": datetime.now() - timedelta(hours=6),
                "url": "https://icar.org.in/news3"
            },
            {
                "title": "किसान क्रेडिट कार्ड योजना में बदलाव",
                "content": "किसान क्रेडिट कार्ड योजना में नए नियम लागू किए गए हैं।",
                "source": "Krishi Jagran",
                "published_at": datetime.now() - timedelta(hours=8),
                "url": "https://krishijagran.com/news4"
            },
            {
                "title": "जैविक खेती को बढ़ावा - सरकारी योजना",
                "content": "सरकार ने जैविक खेती को बढ़ावा देने के लिए नई योजना शुरू की है।",
                "source": "PIB",
                "published_at": datetime.now() - timedelta(hours=10),
                "url": "https://pib.gov.in/news5"
            }
        ]

    def _format_news_summary(self, news: List[Dict[str, Any]]) -> str:
        """Format news summary for response"""
        if not news:
            return "कोई समाचार उपलब्ध नहीं है।"
        
        summary = "ताज़ा कृषि समाचार:\n"
        for item in news[:3]:  # Show top 3
            title = item['title']
            source = item['source']
            summary += f"• {title} ({source})\n"
        
        return summary

    async def get_pesticide_advisories(self) -> Dict[str, Any]:
        """Get latest pesticide advisories"""
        try:
            cache_key = "pesticide_advisories"
            
            # Check cache first
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    logger.info("Returning cached pesticide advisories")
                    return cached_data['data']

            # Get advisories from API or mock data
            advisories = await self._fetch_advisories()
            
            # Cache the result
            self.cache[cache_key] = {
                'data': advisories,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Retrieved {len(advisories.get('advisories', []))} advisories")
            return advisories
            
        except Exception as e:
            logger.error(f"Error getting pesticide advisories: {str(e)}")
            return {
                "error": str(e),
                "advisories": [],
                "summary": "Advisories unavailable"
            }

    async def _fetch_advisories(self) -> Dict[str, Any]:
        """Fetch pesticide advisories"""
        try:
            mock_advisories = self._get_mock_advisories()
            
            return {
                "advisories": mock_advisories,
                "summary": self._format_advisories_summary(mock_advisories),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error fetching advisories: {str(e)}")
            return {"advisories": [], "summary": "Advisories unavailable"}

    def _get_mock_advisories(self) -> List[Dict[str, Any]]:
        """Get mock pesticide advisories"""
        return [
            {
                "title": "Monocrotophos पर प्रतिबंध",
                "content": "Monocrotophos के उपयोग पर 1 दिसंबर 2024 से प्रतिबंध लगाया गया है।",
                "type": "ban",
                "effective_date": "2024-12-01",
                "source": "Government of India"
            },
            {
                "title": "नई कीटनाशक दवा की अनुमति",
                "content": "Neem-based कीटनाशक को सभी फसलों के लिए अनुमति दी गई है।",
                "type": "approval",
                "effective_date": "2024-11-15",
                "source": "ICAR"
            },
            {
                "title": "कीटनाशक उपयोग के नए दिशानिर्देश",
                "content": "कीटनाशक के सुरक्षित उपयोग के लिए नए दिशानिर्देश जारी किए गए हैं।",
                "type": "guidelines",
                "effective_date": "2024-11-01",
                "source": "Ministry of Agriculture"
            }
        ]

    def _format_advisories_summary(self, advisories: List[Dict[str, Any]]) -> str:
        """Format advisories summary"""
        if not advisories:
            return "कोई कीटनाशक सलाह उपलब्ध नहीं है।"
        
        summary = "कीटनाशक सलाह:\n"
        for advisory in advisories[:3]:
            title = advisory['title']
            type_ = advisory['type']
            summary += f"• {title} ({type_})\n"
        
        return summary

    def format_news_response(self, news_data: Dict[str, Any]) -> str:
        """Format news data for user response"""
        try:
            if "error" in news_data:
                return f"माफ़ करें, समाचार उपलब्ध नहीं हैं।"
            
            news = news_data.get('news', [])
            if not news:
                return "वर्तमान में कोई समाचार उपलब्ध नहीं है।"
            
            response = "📰 ताज़ा कृषि समाचार:\n\n"
            
            for item in news[:5]:  # Show top 5
                title = item['title']
                content = item['content']
                source = item['source']
                published_at = item['published_at']
                
                if isinstance(published_at, datetime):
                    time_ago = self._get_time_ago(published_at)
                else:
                    time_ago = "कुछ देर पहले"
                
                response += f"📌 {title}\n"
                response += f"   {content}\n"
                response += f"   📍 {source} • {time_ago}\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting news response: {str(e)}")
            return "समाचार प्राप्त करने में समस्या आ रही है।"

    def _get_time_ago(self, published_at: datetime) -> str:
        """Get time ago string"""
        now = datetime.now()
        diff = now - published_at
        
        if diff.days > 0:
            return f"{diff.days} दिन पहले"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} घंटे पहले"
        else:
            minutes = diff.seconds // 60
            return f"{minutes} मिनट पहले" 