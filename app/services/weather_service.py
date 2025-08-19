import aiohttp
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)

class WeatherService:
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.cache = {}
        self.cache_duration = timedelta(minutes=30)

    async def get_weather(self, location: str) -> Dict[str, Any]:
        """Get current weather for a location"""
        try:
            # Check cache first
            cache_key = location.lower().strip()
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    logger.info(f"Returning cached weather data for {location}")
                    return cached_data['data']

            # Get coordinates first
            coords = await self._get_coordinates(location)
            if not coords:
                return {
                    "location": location,
                    "error": "Location not found",
                    "temperature": None,
                    "humidity": None,
                    "description": "Location not found"
                }

            # Get current weather
            weather_data = await self._get_current_weather(coords['lat'], coords['lon'])
            
            # Get forecast
            forecast_data = await self._get_forecast(coords['lat'], coords['lon'])
            
            # Combine data
            result = {
                "location": location,
                "temperature": weather_data.get('main', {}).get('temp'),
                "temperature_c": weather_data.get('main', {}).get('temp'),  # For compatibility
                "humidity": weather_data.get('main', {}).get('humidity'),
                "description": weather_data.get('weather', [{}])[0].get('description', ''),
                "forecast": forecast_data.get('list', [])[:5],  # Next 5 days
                "timestamp": datetime.now()
            }
            
            # Cache the result
            self.cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Retrieved weather data for {location}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting weather for {location}: {str(e)}")
            return {
                "location": location,
                "error": str(e),
                "temperature": None,
                "humidity": None,
                "description": "Weather data unavailable"
            }

    async def _get_coordinates(self, location: str) -> Optional[Dict[str, float]]:
        """Get coordinates for a location"""
        try:
            url = f"http://api.openweathermap.org/geo/1.0/direct"
            params = {
                "q": f"{location},India",
                "limit": 1,
                "appid": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            return {
                                "lat": data[0]["lat"],
                                "lon": data[0]["lon"]
                            }
            return None
            
        except Exception as e:
            logger.error(f"Error getting coordinates for {location}: {str(e)}")
            return None

    async def _get_current_weather(self, lat: float, lon: float) -> Dict[str, Any]:
        """Get current weather for coordinates"""
        try:
            url = f"{self.base_url}/weather"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"Weather API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error getting current weather: {str(e)}")
            return {}

    async def _get_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        """Get weather forecast for coordinates"""
        try:
            url = f"{self.base_url}/forecast"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        raise Exception(f"Forecast API error: {response.status}")
                        
        except Exception as e:
            logger.error(f"Error getting forecast: {str(e)}")
            return {"list": []}

    def format_weather_response(self, weather_data: Dict[str, Any]) -> str:
        """Format weather data for user response"""
        try:
            if "error" in weather_data:
                return f"माफ़ करें, {weather_data['location']} के लिए मौसम की जानकारी उपलब्ध नहीं है।"
            
            temp = weather_data.get('temperature')
            humidity = weather_data.get('humidity')
            description = weather_data.get('description', '')
            location = weather_data.get('location', '')
            
            if temp is None:
                return f"माफ़ करें, {location} के लिए मौसम की जानकारी उपलब्ध नहीं है।"
            
            response = f"{location} में वर्तमान मौसम:\n"
            response += f"तापमान: {temp}°C\n"
            response += f"आर्द्रता: {humidity}%\n"
            response += f"विवरण: {description}\n"
            
            # Add forecast if available
            forecast = weather_data.get('forecast', [])
            if forecast:
                response += "\nआगामी 5 दिनों का पूर्वानुमान:\n"
                for day in forecast[:5]:
                    date = datetime.fromtimestamp(day['dt']).strftime('%d/%m')
                    temp = day['main']['temp']
                    desc = day['weather'][0]['description']
                    response += f"{date}: {temp}°C, {desc}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting weather response: {str(e)}")
            return "मौसम की जानकारी प्राप्त करने में समस्या आ रही है।" 