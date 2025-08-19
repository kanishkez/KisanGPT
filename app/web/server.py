import os
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from app.services.market_service import MarketService
from app.services.weather_service import WeatherService
from app.services.news_service import NewsService

# Load environment variables first
load_dotenv()

# Configure logging after loading env vars
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title='KisanGPT Web',
    description='Agricultural Information System',
    version='1.0.0'
)

# Setup static file serving
static_dir = os.path.join(os.path.dirname(__file__), 'static')
if os.path.exists(static_dir):
    app.mount('/static', StaticFiles(directory=static_dir), name='static')
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
market_service = MarketService()
weather_service = WeatherService()
news_service = NewsService()

class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    location: Optional[str] = None
    crop: Optional[str] = None

@app.get('/')
async def serve_index():
    """Serve the main index.html file"""
    return FileResponse(os.path.join(static_dir, 'index.html'))

@app.post('/api/chat')
async def process_chat(body: ChatRequest) -> Dict[str, Any]:
    """Process chat messages and return relevant information"""
    try:
        # Basic validation
        user_text = body.message.strip()
        if not user_text:
            raise HTTPException(status_code=400, detail='Message is required')

        # Get location and crop info
        location = body.location
        crop = body.crop

        # Determine what data to fetch based on query
        has_market_query = any(word in user_text.lower() for word in ['price', 'rate', 'market', 'mandi', 'crop'])
        has_weather_query = any(word in user_text.lower() for word in ['weather', 'temperature', 'rain', 'climate'])

        # Prepare response
        response_parts = []

        # Fetch required data in parallel
        tasks = []
        if has_weather_query and location:
            tasks.append(('weather', weather_service.get_weather(location)))
        if has_market_query or crop:
            tasks.append(('market', market_service.get_market_prices(crop=crop, mandi=location)))
        if 'news' in user_text.lower() or 'pest' in user_text.lower():
            tasks.append(('news', news_service.get_pesticide_news()))

        # Execute tasks
        results = {}
        if tasks:
            try:
                responses = await asyncio.gather(*(task[1] for task in tasks), return_exceptions=True)
                for (key, _), response in zip(tasks, responses):
                    if not isinstance(response, Exception):
                        results[key] = response
            except Exception as e:
                logger.error(f"Error executing tasks: {e}")
                raise HTTPException(status_code=500, detail="An error occurred while processing your request")

        # Build response
        if 'market' in results:
            market_data = results['market']
            if market_data and not "error" in market_data:
                response_parts.append(market_service.format_market_response(market_data))

        if 'weather' in results:
            weather = results['weather']
            if weather and not isinstance(weather, Exception):
                weather_info = f"""## Weather in {weather.get('location', location)}

| Condition | Value |
|-----------|-------|
| Temperature | 🌡️ {weather.get('temperature_c', 'N/A')}°C |
| Humidity | 💧 {weather.get('humidity', 'N/A')}% |
| Description | ☁️ {weather.get('description', 'N/A')} |"""
                response_parts.append(weather_info)

        if 'news' in results:
            news = results['news']
            if news and news.get('items'):
                news_info = "\n## Recent Agricultural Updates\n"
                for item in news['items'][:3]:
                    news_info += f"* {item.get('title', '')}\n"
                response_parts.append(news_info)

        # Get crop recommendations
        if any(word in user_text.lower() for word in ['grow', 'plant', 'farming', 'cultivation', 'soil']):
            if location:
                market_data = await market_service.get_market_prices(mandi=location)
                if market_data and not "error" in market_data:
                    response_parts.append(f"\n## Crop Recommendations for {location}\n")
                    response_parts.append(market_service.format_market_response(market_data))

        # Format final response
        response = "\n\n".join(response_parts) if response_parts else (
            "I can help you with:\n"
            "- Current market prices 💰\n"
            "- Weather information ☁️\n"
            "- Agricultural news and updates 📰\n"
            "- Crop recommendations 🌾\n\n"
            "Just ask me about any of these topics!"
        )
        
        return {"response": response}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")



