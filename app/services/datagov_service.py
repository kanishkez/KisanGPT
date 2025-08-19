import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

class DataGovService:
    """Service for fetching and caching data from data.gov.in APIs"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.data.gov.in/resource"
        
    async def fetch_weather_data(self, location: str) -> Optional[Dict[str, Any]]:
        """Fetch weather data for a given location"""
        # IMD weather API endpoint
        endpoint = f"{self.base_url}/imd_weather"
        params = {
            "api-key": self.api_key,
            "format": "json",
            "location": location
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_weather_data(data)
        return None
    
    async def fetch_market_prices(self, crop: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch agricultural market prices"""
        # Agmarknet API endpoint
        endpoint = f"{self.base_url}/agmarknet_prices"
        params = {
            "api-key": self.api_key,
            "format": "json",
            "limit": 100
        }
        
        if crop:
            params["filters[commodity]"] = crop
            
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_market_data(data)
        return None
    
    async def fetch_crop_recommendations(self, state: str) -> Optional[Dict[str, Any]]:
        """Fetch crop recommendations based on soil and climate data"""
        endpoint = f"{self.base_url}/crop_recommendations"
        params = {
            "api-key": self.api_key,
            "format": "json",
            "filters[state]": state
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_crop_data(data)
        return None
    
    def _process_weather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format weather data"""
        if not data.get("records"):
            return {}
            
        records = data["records"][0]
        return {
            "temperature": records.get("temperature"),
            "humidity": records.get("humidity"),
            "rainfall": records.get("rainfall"),
            "forecast": records.get("forecast", [])
        }
    
    def _process_market_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format market price data"""
        if not data.get("records"):
            return {}
            
        prices = []
        for record in data["records"]:
            prices.append({
                "market": record.get("market"),
                "commodity": record.get("commodity"),
                "price": record.get("modal_price"),
                "date": record.get("arrival_date")
            })
            
        return {"prices": prices}
    
    def _process_crop_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format crop recommendation data"""
        if not data.get("records"):
            return {}
            
        recommendations = []
        for record in data["records"]:
            recommendations.append({
                "crop": record.get("crop"),
                "season": record.get("season"),
                "soil_type": record.get("soil_type"),
                "rainfall_needed": record.get("rainfall_needed")
            })
            
        return {"recommendations": recommendations}
