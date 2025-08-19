import aiohttp
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

class AgriculturalDataService:
    """Enhanced agricultural data service for LangChain integration"""
    
    def __init__(self):
        self.api_key = settings.DATAGOV_API_KEY or "579b464db66ec23bdd000001b19d189b5ea74357629a8302e0ed3372"
        self.base_url = settings.DATAGOV_BASE_URL
        self.owm_key = settings.OPENWEATHER_API_KEY
        self.owm_base = "https://api.openweathermap.org"
        
        # API Resource IDs
        self.market_resource_id = "9ef84268-d588-465a-a308-a864a43d0070"
        self.weather_resource_id = "fd37f385-b9ae-4e59-8d4a-1c66e5202be3"
        self.crop_resource_id = "4178b5d3-94f9-4d20-b2a0-a47ad36f7151"

        # Common commodity aliases for Indian mandi data
        self._alias_map = {
            "cotton": ["cotton", "kapas", "cotton (kapas)", "kapas (fardar)", "cotton unginned"],
            "onion": ["onion", "pyaz", "pyaaz"],
            "potato": ["potato", "aloo"],
            "wheat": ["wheat", "gehun", "gehu"],
            "rice": ["rice", "paddy", "dhan"],
            "paddy": ["paddy", "dhan", "rice"],
            "maize": ["maize", "corn", "makka"],
            "chickpea": ["chickpea", "gram", "chana"],
            "bengal gram": ["bengal gram", "chana"],
            "green gram": ["green gram", "moong"],
            "black gram": ["black gram", "urad"],
            "pigeon pea": ["pigeon pea", "arhar", "toor", "tur"],
            "sugarcane": ["sugarcane", "ganna"],
        }

        # Known market/district hints by state for fallback filtering
        self._state_market_hints: Dict[str, List[str]] = {
            "maharashtra": [
                "mumbai","thane","pune","nashik","lasalgaon","nagpur","aurangabad","kolhapur","solapur","jalgaon","latur","satara","sangli","ahmednagar","amravati","akola","nanded","beed","wardha","yavatmal","buldhana","parbhani"
            ],
            "gujarat": ["ahmedabad","rajkot","surat","vadodara","bhavnagar","junagadh","jamnagar","bhuj"],
            "karnataka": ["bengaluru","mysuru","hubballi","belagavi","mangaluru","tumakuru","davangere"],
            "tamil nadu": ["chennai","coimbatore","madurai","salem","tiruchirappalli","erode","vellore"],
            "telangana": ["hyderabad","warangal","nizamabad","khammam","karimnagar"],
            "andhra pradesh": ["vijayawada","guntur","vizag","visakhapatnam","tirupati","kurnool"],
            "rajasthan": ["jaipur","jodhpur","udaipur","ajmer","kota","bhilwara","alwar"],
            "uttar pradesh": ["lucknow","kanpur","varanasi","meerut","agra","bareilly","ghaziabad","allahabad","prayagraj"],
            "madhya pradesh": ["bhopal","indore","ujjain","jabalpur","gwalior","sagar","satna"],
            "west bengal": ["kolkata","howrah","siliguri","durgapur","asansol","malda"],
            "punjab": ["ludhiana","amritsar","jalandhar","patiala","bathinda"],
            "haryana": ["gurugram","faridabad","ambala","karnal","hisar","panipat"],
            "bihar": ["patna","gaya","muzaffarpur","bhagalpur","darbhanga"]
        }

    def _match_market_district(self, rec: Dict[str, Any], hints: List[str]) -> bool:
        name1 = str(rec.get("market", "")).strip().lower()
        name2 = str(rec.get("district", "")).strip().lower()
        simple1 = name1.replace(" ", "")
        simple2 = name2.replace(" ", "")
        for h in hints:
            h1 = h.lower()
            if h1 in name1 or h1 in name2 or h1 in simple1 or h1 in simple2:
                return True
        return False

    def _aliases_for(self, crop: Optional[str]) -> List[str]:
        key = (crop or "").strip().lower()
        if not key:
            return []
        # Gather aliases; include the key itself
        aliases = set([key])
        if key in self._alias_map:
            for a in self._alias_map[key]:
                aliases.add(a.lower())
        # Also include space/paren stripped variants
        more = set()
        for a in aliases:
            more.add(a.replace(" ", ""))
        aliases.update(more)
        return list(aliases)

    async def _owm_geocode(self, location: str) -> Optional[Dict[str, Any]]:
        """Resolve a location string to lat/lon via OpenWeather geocoding."""
        if not self.owm_key:
            return None
        try:
            url = f"{self.owm_base}/geo/1.0/direct"
            params = {"q": location, "limit": 1, "appid": self.owm_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data:
                            return data[0]
        except Exception as e:
            logger.warning(f"OWM geocode failed for '{location}': {e}")
        return None

    async def _owm_current(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Fetch current weather from OpenWeather."""
        if not self.owm_key:
            return None
        try:
            url = f"{self.owm_base}/data/2.5/weather"
            params = {"lat": lat, "lon": lon, "appid": self.owm_key, "units": "metric"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.warning(f"OWM current weather failed: {e}")
        return None

    async def _owm_forecast(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Fetch short forecast (3-hourly) from OpenWeather."""
        if not self.owm_key:
            return None
        try:
            url = f"{self.owm_base}/data/2.5/forecast"
            params = {"lat": lat, "lon": lon, "appid": self.owm_key, "units": "metric", "cnt": 8}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.warning(f"OWM forecast failed: {e}")
        return None

    async def get_openweather_summary(self, location: Optional[str]) -> str:
        """Return a concise markdown summary of current weather and short forecast for location.
        Falls back to empty string if not available."""
        if not location:
            return ""
        try:
            geo = await self._owm_geocode(location)
            if not geo:
                return ""
            lat, lon = geo.get("lat"), geo.get("lon")
            if lat is None or lon is None:
                return ""
            current, forecast = await self._owm_current(lat, lon), await self._owm_forecast(lat, lon)
            parts: List[str] = []
            if current:
                name = current.get("name") or location
                weather_desc = (current.get("weather") or [{}])[0].get("description", "-")
                main = current.get("main") or {}
                wind = current.get("wind") or {}
                temp = main.get("temp")
                feels = main.get("feels_like")
                humidity = main.get("humidity")
                wind_speed = wind.get("speed")
                parts.append("### Live Weather (OpenWeather)")
                parts.append(f"**Location:** {name}  |  **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
                parts.append(f"- Condition: {weather_desc}")
                if temp is not None:
                    parts.append(f"- Temperature: {temp}°C (feels like {feels}°C)")
                if humidity is not None:
                    parts.append(f"- Humidity: {humidity}%")
                if wind_speed is not None:
                    parts.append(f"- Wind: {wind_speed} m/s")
                parts.append("")
            if forecast and forecast.get("list"):
                parts.append("### Next 24h Forecast (3-hourly)")
                for item in forecast["list"][:6]:
                    dt_txt = item.get("dt_txt", "")
                    wdesc = (item.get("weather") or [{}])[0].get("description", "-")
                    t = (item.get("main") or {}).get("temp")
                    parts.append(f"- {dt_txt}: {wdesc}, {t}°C")
                parts.append("")
            return "\n".join(parts)
        except Exception as e:
            logger.warning(f"OpenWeather summary error: {e}")
            return ""
    
    async def get_market_prices_optimized(self, location: Optional[str] = None, crop: Optional[str] = None) -> str:
        """Get optimized market prices with a logical fallback strategy."""
        try:
            params: Dict[str, Any] = {"limit": "10"}
            response: Dict[str, Any] = {}
            note = None

            # Attempt 1: Strict search (State + Crop)
            if location and crop:
                logger.debug(f"[Market] Attempt 1: Strict search for '{crop}' in '{location}'")
                params["filters[state]"] = location.title()
                params["filters[commodity]"] = crop.title()
                response = await self._make_request(self.market_resource_id, params)

            # Attempt 2: Pan-India fallback for crop if strict search fails
            if crop and not response.get("records"):
                logger.debug(f"[Market] Attempt 2: Pan-India search for '{crop}'")
                params = {"limit": "10", "filters[commodity]": crop.title()}
                response = await self._make_request(self.market_resource_id, params)
                if response.get("records"):
                    note = f"No recent records found for '{crop}' in '{location}'. Showing recent pan-India prices instead."

            # Attempt 3: State-only search if no crop was specified
            if location and not crop and not response.get("records"):
                logger.debug(f"[Market] Attempt 3: State-only search for any crop in '{location}'")
                params = {"limit": "10", "filters[state]": location.title()}
                response = await self._make_request(self.market_resource_id, params)

            # Final check: if no records found after all attempts, return the 'no data' message
            if not response.get("records"):
                logger.debug("[Market] All fallbacks failed. Returning 'no data' message.")
                return self._local_no_data_message(location, crop)

            # --- Build Response --- #
            records = response.get("records", [])
            result_lines = [
                f"## Current Market Prices (Latest Records)",
                f"**Location Filter:** {location or 'All India'}",
                f"**Crop Filter:** {crop or 'All Crops'}"
            ]
            if note:
                result_lines.append(f"_Note: {note}_")
            result_lines.append("")

            if records:
                high_profit_crops = []
                medium_profit_crops = []
                other_crops = []

                for record in records[:10]:
                    try:
                        price_raw = record.get("modal_price", "N/A")
                        price_num = float(str(price_raw).replace(",", "")) if price_raw not in ("N/A", None, "") else None
                        price_line = f"• {record.get('commodity', '')} at {record.get('market', '')}, {record.get('state', '')}: ₹{price_raw}/quintal (Date: {record.get('arrival_date', 'N/A')})"
                        
                        if price_num is not None:
                            if price_num > 5000:
                                high_profit_crops.append(price_line)
                            elif price_num > 2000:
                                medium_profit_crops.append(price_line)
                            else:
                                other_crops.append(price_line)
                        else:
                            other_crops.append(price_line)
                    except (ValueError, TypeError):
                        continue
                
                if other_crops:
                    result_lines.extend(other_crops)
                
                if high_profit_crops:
                    result_lines.append("\n### High Profit Potential (>₹5000/quintal):")
                    result_lines.extend(high_profit_crops)
                
                if medium_profit_crops:
                    result_lines.append("\n### Medium Profit Potential (₹2000-5000/quintal):")
                    result_lines.extend(medium_profit_crops)

            result_lines.append("\n**Data Source:** Government of India data.gov.in portal")
            return "\n".join(result_lines)
        
        except Exception as e:
            logger.error(f"Error in market analysis: {e}")
            return f"An unexpected error occurred while fetching market data: {e}"

    def _local_mandi_fallback(self, location: Optional[str], crop: Optional[str], limit: int = 10) -> Optional[str]:
        """Return a cached price summary from data/mandi_qna.jsonl when API is unavailable.
        Tries to match crop and location substrings in the 'question' field.
        """
        import os, json, re
        path = os.path.join("data", "mandi_qna.jsonl")
        if not os.path.exists(path):
            return None
        loc = (location or "").strip().lower()
        crp = (crop or "").strip().lower()
        primary = []
        secondary = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    q = str(obj.get("question", ""))
                    a = obj.get("answer")
                    ql = q.lower()
                    if crp and crp not in ql:
                        continue
                    score_loc = 0
                    if loc:
                        if loc in ql:
                            score_loc = 2
                        # also check common state names capitalization patterns
                    # extract simple market/state from question like "... in Surat (Gujarat)?"
                    market = None
                    state = None
                    m = re.search(r" in\s+([^\(\)]+?)\s*\(([^\)]+)\)\?", q)
                    if m:
                        market = m.group(1).strip()
                        state = m.group(2).strip()
                        if loc and (loc in market.lower() or loc in state.lower()):
                            score_loc = max(score_loc, 2)
                    item = {"q": q, "price": a, "market": market, "state": state}
                    if score_loc >= 2:
                        primary.append(item)
                    else:
                        secondary.append(item)
                    if len(primary) >= limit:
                        break
            dataset = primary or secondary[:limit]
            if not dataset:
                return None
            lines = ["## Current Market Prices", f"**Location Filter:** {location or 'All India'}", f"**Crop Filter:** {crop or 'All Crops'}", ""]
            for it in dataset[:limit]:
                mk = (it.get("market") or "").strip()
                st = (it.get("state") or "").strip()
                price = it.get("price")
                if mk or st:
                    lines.append(f"• {crop or 'Commodity'} at {mk}{(', ' + st) if st else ''}: ₹{price}/quintal")
                else:
                    lines.append(f"• {it.get('q')}: ₹{price}/quintal")
            return "\n".join(lines)
        except Exception:
            return None

    def _local_no_data_message(self, location: Optional[str], crop: Optional[str]) -> str:
        """Return a specific message indicating no data was found, for the LLM to process."""
        lines = [
            "## Current Market Prices",
            f"**Location Filter:** {location or 'All India'}",
            f"**Crop Filter:** {crop or 'All Crops'}",
            "",
            "_Note: No recent market records were found for the specified filters. Please try specifying a state and a commodity for more precise results._",
            "",
            "**Data Source:** Government of India data.gov.in portal"
        ]
        return "\n".join(lines)

    async def get_crop_data(self, location: Optional[str] = None, crop: Optional[str] = None) -> str:
        """Get comprehensive crop data for LangChain agent"""
        try:
            result_parts = []
            
            # Get market data if available
            if location or crop:
                market_data = await self.get_market_prices(crop)
                if market_data and "prices" in market_data and market_data["prices"]:
                    result_parts.append("**Market Prices:**")
                    for price_info in market_data["prices"][:5]:  # Limit to top 5
                        result_parts.append(f"- {price_info['commodity']}: ₹{price_info['price']} at {price_info['market']}")
            
            # Get regional recommendations if location provided
            if location:
                regional_data = await self.get_regional_recommendations(location)
                if regional_data and "recommendations" in regional_data and regional_data["recommendations"]:
                    result_parts.append(f"\n**Top Crops for {location}:**")
                    for rec in regional_data["recommendations"][:3]:
                        result_parts.append(f"- {rec['crop']}: Avg yield {rec['average_yield']} ({rec['confidence']} confidence)")
            
            return "\n".join(result_parts) if result_parts else "No specific crop data available"
            
        except Exception as e:
            logger.error(f"Error fetching crop data: {e}")
            return f"Error fetching crop data: {str(e)}"
    
    async def _make_request(self, resource_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make API request with error handling"""
        request_params = params or {}
            
        url = f"{self.base_url}/resource/{resource_id}"
        request_params.update({
            "api-key": self.api_key,
            "format": "json",
            "offset": "0",
            "limit": "10"
        })
        
        try:
            async with aiohttp.ClientSession() as session:
                # Respect SSL verification setting (disable for local dev if configured)
                ssl_param = None if settings.DATAGOV_VERIFY_SSL else False
                headers = {"x-api-key": self.api_key} if self.api_key else {}
                async with session.get(url, params=request_params, headers=headers, ssl=ssl_param) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    return {"error": f"API returned status {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_market_prices(self, crop: Optional[str] = None) -> Dict[str, Any]:
        """Get agricultural market prices"""
        params: Dict[str, Any] = {}
        if crop:
            params["filters[commodity]"] = crop.lower()
            
        response = await self._make_request(self.market_resource_id, params)
        
        if "error" in response:
            return response
            
        if "records" in response:
            return {
                "prices": [
                    {
                        "market": record.get("market", ""),
                        "price": record.get("modal_price", ""),
                        "commodity": record.get("commodity", ""),
                        "date": record.get("arrival_date", "")
                    }
                    for record in response["records"]
                ]
            }
        return {"prices": []}
    
    async def get_regional_recommendations(self, state: str) -> Dict[str, Any]:
        """Get regional crop recommendations"""
        crop_data = await self.get_crop_production(state)
        
        if "error" in crop_data:
            return crop_data
            
        if not crop_data["crops"]:
            return {"recommendations": []}
            
        # Analyze crop data for recommendations
        crop_stats = {}
        for crop in crop_data["crops"]:
            name = crop["name"]
            if name not in crop_stats:
                crop_stats[name] = {"total_yield": 0, "count": 0}
                
            try:
                crop_yield = float(crop["yield"]) if crop["yield"] != "N/A" else 0
                crop_stats[name]["total_yield"] += crop_yield
                crop_stats[name]["count"] += 1
            except (ValueError, TypeError):
                continue
        
        # Generate recommendations based on average yield
        recommendations = []
        for crop, stats in crop_stats.items():
            if stats["count"] > 0:
                avg_yield = stats["total_yield"] / stats["count"]
                recommendations.append({
                    "crop": crop,
                    "average_yield": round(avg_yield, 2),
                    "confidence": "High" if stats["count"] >= 5 else "Medium"
                })
        
        # Sort by average yield
        recommendations.sort(key=lambda x: x["average_yield"], reverse=True)
        
        return {
            "recommendations": recommendations[:5],
            "state": state
        }
    
    async def get_crop_production(self, state: str) -> Dict[str, Any]:
        """Get crop production data"""
        params = {"filters[state_name]": state}
        
        response = await self._make_request(self.crop_resource_id, params)
        
        if "error" in response:
            return response
            
        if "records" in response:
            return {
                "crops": [
                    {
                        "name": record.get("crop", ""),
                        "area": record.get("area", "N/A"),
                        "production": record.get("production", "N/A"),
                        "yield": record.get("yield", "N/A"),
                        "year": record.get("crop_year", "")
                    }
                    for record in response["records"]
                ]
            }
        return {"crops": []}

class DataGovService:
    def __init__(self):
        # Use env-configured key and base URL
        self.api_key = settings.DATAGOV_API_KEY or ""
        self.base_url = settings.DATAGOV_BASE_URL
        
        # API Resource IDs
        self.market_resource_id = "9ef84268-d588-465a-a308-a864a43d0070"
        self.weather_resource_id = "fd37f385-b9ae-4e59-8d4a-1c66e5202be3"
        self.crop_resource_id = "4178b5d3-94f9-4d20-b2a0-a47ad36f7151"
    
    async def _make_request(self, resource_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make API request with error handling"""
        request_params = params or {}
            
        url = f"{self.base_url}/resource/{resource_id}"
        request_params.update({
            "api-key": self.api_key,
            "format": "json",
            "offset": "0",
            "limit": "10"
        })
        
        try:
            async with aiohttp.ClientSession() as session:
                # Respect SSL verification setting like the main service
                ssl_param = None if settings.DATAGOV_VERIFY_SSL else False
                headers = {"x-api-key": self.api_key} if self.api_key else {}
                async with session.get(url, params=request_params, headers=headers, ssl=ssl_param) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    return {"error": f"API returned status {response.status}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_market_prices(self, crop: Optional[str] = None) -> Dict[str, Any]:
        """Get agricultural market prices"""
        params: Dict[str, Any] = {}
        if crop:
            params["filters[commodity]"] = crop.lower()
            
        response = await self._make_request(self.market_resource_id, params)
        
        if "error" in response:
            return response
            
        if "records" in response:
            return {
                "prices": [
                    {
                        "market": record.get("market", ""),
                        "price": record.get("modal_price", ""),
                        "commodity": record.get("commodity", ""),
                        "date": record.get("arrival_date", "")
                    }
                    for record in response["records"]
                ]
            }
        return {"prices": []}
    
    async def get_weather_data(self, location: str) -> Dict[str, Any]:
        """Get weather data for location"""
        params: Dict[str, Any] = {
            "filters[station]": location.upper(),
            "filters[unit]": "CELSIUS"
        }
        
        response = await self._make_request(self.weather_resource_id, params)
        
        if "error" in response:
            return {
                "location": location,
                "error": response["error"],
                "message": "Unable to fetch weather data"
            }
            
        if "records" in response and response["records"]:
            record = response["records"][0]
            return {
                "location": location,
                "temperature": record.get("temperature", "N/A"),
                "humidity": record.get("humidity", "N/A"),
                "rainfall": record.get("rainfall", "N/A"),
                "last_updated": record.get("timestamp", datetime.now().isoformat()),
                "forecast": record.get("forecast", [])
            }
        return {
            "location": location,
            "error": "No data found",
            "message": "No weather data available for this location"
        }
    
    async def get_crop_production(self, state: str) -> Dict[str, Any]:
        """Get crop production data"""
        params = {"filters[state_name]": state}
        
        response = await self._make_request(self.crop_resource_id, params)
        
        if "error" in response:
            return response
            
        if "records" in response:
            return {
                "crops": [
                    {
                        "name": record.get("crop", ""),
                        "area": record.get("area", "N/A"),
                        "production": record.get("production", "N/A"),
                        "yield": record.get("yield", "N/A"),
                        "year": record.get("crop_year", "")
                    }
                    for record in response["records"]
                ]
            }
        return {"crops": []}
    
    async def get_regional_recommendations(self, state: str) -> Dict[str, Any]:
        """Get regional crop recommendations"""
        crop_data = await self.get_crop_production(state)
        
        if "error" in crop_data:
            return crop_data
            
        if not crop_data["crops"]:
            return {"recommendations": []}
            
        # Analyze crop data for recommendations
        crop_stats = {}
        for crop in crop_data["crops"]:
            name = crop["name"]
            if name not in crop_stats:
                crop_stats[name] = {"total_yield": 0, "count": 0}
                
            try:
                crop_yield = float(crop["yield"]) if crop["yield"] != "N/A" else 0
                crop_stats[name]["total_yield"] += crop_yield
                crop_stats[name]["count"] += 1
            except (ValueError, TypeError):
                continue
        
        # Generate recommendations based on average yield
        recommendations = []
        for crop, stats in crop_stats.items():
            if stats["count"] > 0:
                avg_yield = stats["total_yield"] / stats["count"]
                recommendations.append({
                    "crop": crop,
                    "average_yield": round(avg_yield, 2),
                    "confidence": "High" if stats["count"] >= 5 else "Medium"
                })
        
        # Sort by average yield
        recommendations.sort(key=lambda x: x["average_yield"], reverse=True)
        
        return {
            "recommendations": recommendations[:5],
            "state": state
        }
