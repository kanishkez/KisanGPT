import httpx
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)

# Configure from environment/.env with safe defaults
API_KEY = settings.DATAGOV_API_KEY or "579b464db66ec23bdd000001b19d189b5ea74357629a8302e0ed3372"
API_BASE = f"{settings.DATAGOV_BASE_URL.rstrip('/')}{settings.MARKET_PRICES_ENDPOINT}"

class MarketService:
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour since this is daily data

    async def get_market_prices(self, crop: Optional[str] = None, mandi: Optional[str] = None) -> Dict[str, Any]:
        """Get market prices for crops from data.gov.in API"""
        try:
            cache_key = f"{crop}_{mandi}" if crop and mandi else crop or mandi
            
            # Check cache first
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if datetime.now() - cached_data['timestamp'] < self.cache_duration:
                    logger.info(f"Returning cached market data for {cache_key}")
                    return cached_data['data']

            # Get prices from data.gov.in API
            prices = await self._fetch_prices(crop, mandi)
            
            # Cache the result
            self.cache[cache_key] = {
                'data': prices,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Retrieved market prices for {cache_key}")
            return prices
            
        except Exception as e:
            logger.error(f"Error getting market prices: {str(e)}")
            return {
                "error": str(e),
                "prices": [],
                "summary": "Market prices unavailable"
            }

    async def _fetch_prices(self, crop: Optional[str] = None, mandi: Optional[str] = None) -> Dict[str, Any]:
        """Fetch prices from data.gov.in API"""
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": 100,
            "sort[arrival_date]": "desc"
        }
        
        if crop:
            params["filters[commodity]"] = crop.upper()
        if mandi:
            params["filters[market]"] = mandi.upper()
        
        try:
            logger.debug(f"[MarketService] Requesting: {API_BASE} params={params}")
            async with httpx.AsyncClient() as client:
                response = await client.get(API_BASE, params=params)
                response.raise_for_status()
                data = response.json()
                
                if "records" in data and data["records"]:
                    # Process and format the records
                    formatted_prices = [{
                        "market": record.get("market", "N/A"),
                        "commodity": record.get("commodity", "N/A"),
                        "variety": record.get("variety", "N/A"),
                        "price": record.get("modal_price", "N/A"),
                        "min_price": record.get("min_price", "N/A"),
                        "max_price": record.get("max_price", "N/A"),
                        "unit": record.get("unit", "N/A"),
                        "date": record.get("arrival_date", datetime.now().strftime("%Y-%m-%d"))
                    } for record in data["records"]]
                    
                    # Calculate average price
                    valid_prices = [
                        float(str(p["price"]).replace(",", ""))
                        for p in formatted_prices
                        if p["price"] not in (None, "", "N/A") and str(p["price"]).replace(",", "").replace(".", "").isdigit()
                    ]
                    avg_price = sum(valid_prices) / len(valid_prices) if valid_prices else None
                    
                    return {
                        "error": None,
                        "prices": formatted_prices,
                        "summary": {
                            "total_records": len(formatted_prices),
                            "average_price": round(avg_price, 2) if avg_price else "N/A",
                            "unit": formatted_prices[0]["unit"] if formatted_prices else "N/A",
                            "last_updated": datetime.now().isoformat()
                        }
                    }
                return {
                    "error": "No data found",
                    "prices": [],
                    "summary": "No price data available"
                }
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {str(e)}")
            return {
                "error": "HTTP Error",
                "message": str(e),
                "prices": [],
                "summary": "Error fetching market prices"
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return {
                "error": "Parse Error",
                "message": str(e),
                "prices": [],
                "summary": "Error parsing market data"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "error": "Unknown Error",
                "message": str(e),
                "prices": [],
                "summary": "Unexpected error occurred"
            }

    def _summarize_prices(self, analyzed_data: List[tuple]) -> str:
        """Summarize market prices into a readable format with recommendations"""
        if not analyzed_data:
            return "No market data available"

        summary_parts = []
        
        # Top commodities by demand and price
        summary_parts.append("Based on current market analysis, here are the recommended crops:")
        summary_parts.append("\n### Current Market Status")
        summary_parts.append("\n| Crop | Average Price (₹/qtl) | Active Markets | Price Range (₹/qtl) |")
        summary_parts.append("|------|-------------------|----------------|-----------------|")
        
        # Show top 5 commodities
        for commodity, data in analyzed_data[:5]:
            avg_price = data['modal_price'] / data['count']
            markets = len(data['markets'])
            min_price = int(data['min_price'])
            max_price = int(data['max_price'])
            price_variation = ((max_price - min_price) / avg_price) * 100  # Calculate price variation percentage
            
            summary_parts.append(
                f"| {commodity} | {int(avg_price)} | {markets} | {min_price}-{max_price} |"
            )

        # Market Analysis
        summary_parts.append("\n### Market Analysis")
        
        # High value crops
        high_value_crops = [
            (commodity, data) for commodity, data in analyzed_data[:5]
            if data['modal_price'] / data['count'] > 3000
        ]
        if high_value_crops:
            summary_parts.append("\n**High-Value Crops:**")
            for commodity, data in high_value_crops:
                avg_price = int(data['modal_price'] / data['count'])
                markets = len(data['markets'])
                summary_parts.append(f"- {commodity} (₹{avg_price}/qtl in {markets} markets)")

        # Market coverage
        wide_market_crops = sorted(
            analyzed_data[:5],
            key=lambda x: len(x[1]['markets']),
            reverse=True
        )
        summary_parts.append("\n**Market Availability:**")
        for commodity, data in wide_market_crops[:3]:
            markets = len(data['markets'])
            summary_parts.append(f"- {commodity} is traded in {markets} markets")

        # Price stability analysis
        stability_analysis = []
        for commodity, data in analyzed_data[:5]:
            avg_price = data['modal_price'] / data['count']
            price_range = data['max_price'] - data['min_price']
            variation = (price_range / avg_price) * 100
            markets = len(data['markets'])
            if markets >= 3:  # Only consider crops with significant market presence
                stability_analysis.append((commodity, variation, markets))

        if stability_analysis:
            stable_crops = sorted(stability_analysis, key=lambda x: x[1])[:3]
            summary_parts.append("\n**Price Stability:**")
            for commodity, variation, markets in stable_crops:
                summary_parts.append(f"- {commodity} (Price variation: {variation:.1f}% across {markets} markets)")

        # Overall recommendations
        summary_parts.append("\n### Key Recommendations")
        summary_parts.append("\nBased on current market conditions:")

        # Best overall options
        best_options = []
        for commodity, data in analyzed_data[:3]:
            avg_price = data['modal_price'] / data['count']
            markets = len(data['markets'])
            price_range = data['max_price'] - data['min_price']
            variation = (price_range / avg_price) * 100
            
            if markets >= 3 and variation < 50:  # Reasonable stability and market presence
                best_options.append(f"1. **{commodity}** - Balanced choice with good market presence "
                                 f"(₹{int(avg_price)}/qtl in {markets} markets)")
                break

        # Add market coverage recommendation
        if wide_market_crops:
            best_markets = wide_market_crops[0]
            summary_parts.append(f"2. **{best_markets[0]}** has the widest market presence "
                              f"({len(best_markets[1]['markets'])} markets)")

        # Add stability recommendation
        if stability_analysis:
            most_stable = min(stability_analysis, key=lambda x: x[1])
            summary_parts.append(f"3. **{most_stable[0]}** shows the most stable pricing "
                              f"(variation: {most_stable[1]:.1f}%)")

        # Add risk management note
        summary_parts.append("\n> 📈 Note: Prices may vary based on quality, quantity, and seasonal factors. "
                          "Consider market accessibility and transportation costs in your decision.")
        return "\n".join(summary_parts)

    async def _get_all_prices(self) -> Dict[str, Any]:
        """Get all available prices"""
        return await self._fetch_prices()

    def format_market_response(self, market_data: Dict[str, Any]) -> str:
        """Format market data for user response"""
        try:
            if "error" in market_data:
                return "Sorry, market prices are currently unavailable."
            
            prices = market_data.get('prices', [])
            if not prices:
                return "No market prices available at the moment."
            
            response = "📊 Current Market Prices:\n\n"
            
            # Group by crop to show best price for each
            crop_groups = {}
            for price in prices:
                crop = price.get('commodity', price.get('crop', 'Unknown'))
                max_price = float(price.get('max_price', 0)) if price.get('max_price') else 0
                if crop not in crop_groups or max_price > crop_groups[crop].get('max_price', 0):
                    crop_groups[crop] = price
            
            # Sort by price and take top 10
            top_prices = sorted(crop_groups.values(), key=lambda x: float(x.get('max_price', 0)) if x.get('max_price') else 0, reverse=True)[:10]
            
            for price in top_prices:
                try:
                    crop = price.get('commodity', '').title() or price.get('crop', '').title()
                    mandi = price.get('market', '') or price.get('mandi', '')
                    state = price.get('state', '')
                    district = price.get('district', '')
                    min_price = float(price.get('min_price', 0))
                    max_price = float(price.get('max_price', 0))
                    modal_price = float(price.get('modal_price', 0))
                    unit = price.get('unit', 'quintal')
                    date = price.get('date', 'Today')
                    if isinstance(date, datetime):
                        date = date.strftime('%d/%m/%Y')
                except (KeyError, ValueError, TypeError) as e:
                    logger.error(f"Error processing price data: {e}")
                    continue
                
                response += f"🌾 {crop}\n"
                response += f"   📍 {mandi}, {district}, {state}\n"
                response += f"   💰 Range: ₹{min_price:,.0f}-{max_price:,.0f}\n"
                response += f"   💵 Most Common: ₹{modal_price:,.0f} per {unit}\n"
                response += f"   📅 {date}\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting market response: {str(e)}")
            return "मंडी कीमतें प्राप्त करने में समस्या आ रही है।"

    async def get_crop_advice(self, crop: str, location: Optional[str] = None) -> str:
        """Get crop-specific advice based on current prices and conditions"""
        try:
            prices = await self.get_market_prices(crop=crop)
            
            if not prices or "error" in prices or not prices.get('prices'):
                return f"No price information available for {crop.title()} at the moment."
            
            # Get average price with error handling
            try:
                price_list = prices['prices']
                valid_prices = []
                for p in price_list:
                    try:
                        min_price = float(p.get('min_price', 0))
                        max_price = float(p.get('max_price', 0))
                        if min_price > 0 and max_price > 0:
                            valid_prices.append((min_price + max_price) / 2)
                    except (ValueError, TypeError):
                        continue
                
                if not valid_prices:
                    return f"Unable to calculate average price for {crop.title()} due to invalid data."
                
                avg_price = sum(valid_prices) / len(valid_prices)
                
                advice = f"🌾 Current average price for {crop.title()}: ₹{avg_price:,.0f} per quintal\n\n"
                
                # Add price trend advice with more detailed information
                if avg_price > 3000:
                    advice += "📈 Prices are good. Favorable time to sell.\n"
                    advice += "   • Market sentiment is positive\n"
                    advice += "   • Consider selling if you have storage costs"
                elif avg_price > 2000:
                    advice += "📊 Prices are normal. Consider holding for better rates.\n"
                    advice += "   • Monitor market trends\n"
                    advice += "   • Watch for seasonal price variations"
                else:
                    advice += "📉 Prices are low. Consider these options:\n"
                    advice += "   • Store if storage costs are reasonable\n"
                    advice += "   • Watch for minimum support price announcements"
                
                return advice
                
            except Exception as calc_error:
                logger.error(f"Error calculating average price: {calc_error}")
                return f"Unable to analyze prices for {crop.title()} due to calculation error."
            
        except Exception as e:
            logger.error(f"Error getting crop advice: {str(e)}")
            return "Unable to fetch crop advice at the moment. Please try again later." 