import logging
import base64
from typing import Optional, Dict, Any, List
from PIL import Image
import io
import asyncio

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import BaseTool, tool
from langchain.schema import HumanMessage, AIMessage
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field

from app.config import settings
from app.services.agricultural_data import AgriculturalDataService

logger = logging.getLogger(__name__)

class ImageAnalysisInput(BaseModel):
    """Input for image analysis tool"""
    image_data: str = Field(description="Base64 encoded image data")
    query: str = Field(description="Question about the image")

@tool
async def get_agricultural_data(location: Optional[str] = None, crop: Optional[str] = None) -> str:
    """Get optimized agricultural market data with profit analysis.
    
    Args:
        location: Location/state name (optional)
        crop: Crop name (optional)
    
    Returns:
        Market prices and profit recommendations
    """
    try:
        agri_service = AgriculturalDataService()
        
        # Use optimized data fetching (50 records max instead of 1000+)
        market_data = await agri_service.get_market_prices_optimized(location=location, crop=crop)
        
        return market_data
    except Exception as e:
        logger.error(f"Error fetching agricultural data: {e}")
        return f"Error fetching agricultural data: {str(e)}"

@tool
def analyze_agricultural_image(image_data: str, query: str, gemini_model) -> str:
    """Analyze agricultural images for crop diseases, pests, plant health, or identification.
    
    Args:
        image_data: Base64 encoded image data
        query: Question about the image
        gemini_model: Gemini model instance for analysis
    
    Returns:
        Analysis results with agricultural insights and recommendations
    """
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Create prompt for agricultural image analysis
        prompt = f"""
        You are an expert agricultural consultant analyzing crop images. 
        Please analyze this image and provide detailed insights about:
        
        1. Crop identification (if visible)
        2. Plant health assessment
        3. Disease or pest identification (if any)
        4. Growth stage analysis
        5. Recommendations for improvement
        
        User's specific question: {query}
        
        Provide practical, actionable advice for farmers.
        """
        
        # Use Gemini Vision to analyze the image
        response = gemini_model.invoke([
            HumanMessage(content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ])
        ])
        
        return response.content
    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return f"Error analyzing image: {str(e)}"

class MarketDataInput(BaseModel):
    """Input for market data tool"""
    location: Optional[str] = Field(None, description="Location/mandi name")
    crop: Optional[str] = Field(None, description="Crop name")

class KisanGPTLangChainAgent:
    """LangChain-based agricultural assistant using Gemini 2.5 Pro"""
    
    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        self.setup_agent()
    
    def setup_agent(self):
        """Initialize the LangChain agent with Gemini 2.5 Pro"""
        try:
            # Initialize Gemini model
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",  # Using latest Gemini model
                google_api_key=self.gemini_api_key,
                temperature=0.3,  # Lower temperature for more consistent responses
                convert_system_message_to_human=True
            )
            
            # Initialize tools
            self.tools = [
                get_agricultural_data
            ]
            
            # Create system prompt
            system_prompt = """You are KisanGPT, India's most trusted agricultural AI assistant powered by Google's Gemini 2.5 Pro. You are specifically designed to help farmers maximize their profits and make data-driven agricultural decisions.

CORE IDENTITY & MISSION:
- You are KisanGPT - a specialized agricultural expert, not a general AI assistant
- Your primary mission is to help farmers increase profitability and make informed crop choices
- You provide authoritative, confident advice based on real government data from data.gov.in
- You analyze market trends, price patterns, and regional factors to recommend the most profitable crops

CRITICAL OPERATIONAL RULES:
1. ALWAYS respond in English only - never use Hindi or regional languages
2. NEVER express uncertainty or say "I don't have access to data" - you DO have comprehensive data access
3. MANDATORY: Use get_agricultural_data tool for EVERY agricultural query to fetch live market data
4. ALWAYS analyze the complete dataset provided by the tool before responding
5. Extract location information from user queries automatically (states, districts, regions)
6. Provide confident, authoritative recommendations based on data analysis
7. Focus on profit potential and market demand when suggesting crops

DATA ANALYSIS APPROACH:
- Analyze current market prices across multiple markets and commodities
- Identify crops with high price stability and profit potential
- Consider seasonal demand patterns and regional suitability
- Compare price ranges to determine most profitable options
- Factor in local market conditions and transportation costs
RESPONSE STYLE:
- Be direct, confident, and authoritative in your recommendations
- Provide specific profit estimates and market price data
- Give actionable farming advice with clear next steps
- Include market timing and seasonal considerations
- Always cite data.gov.in as your data source for credibility

EXPERTISE AREAS:
- Crop profitability analysis and selection
- Market price trend analysis and forecasting
- Regional agricultural optimization
- Seasonal crop planning for maximum returns
- Risk assessment and profit maximization strategies
- Agricultural market intelligence and insights

Remember: You are the farmer's trusted advisor for profitable agriculture. Always provide data-backed, confident guidance that helps them make money from their farming operations.
- Current market prices from government databases
- Regional crop production statistics

Always provide practical, actionable advice based on ACTUAL fetched data.
Always end with "— KisanGPT"

LANGUAGE RULE: Respond ONLY in English, never in Hindi, Telugu, Bengali or any other language."""
            
            # Create prompt template
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
            
            # Create agent
            self.agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.prompt
            )
            
            # Create agent executor with forced tool usage
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                verbose=True,
                max_iterations=3,
                early_stopping_method="generate",
                handle_parsing_errors=True,
                memory=ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True
                )
            )
            
            logger.info("LangChain agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up LangChain agent: {e}")
            raise
    
    async def process_query(self, query: str, image_data: Optional[str] = None, context: Dict[str, Any] = None) -> str:
        """Process user query with optional image"""
        try:
            # Extract location and crop from query for forced tool usage
            location = self._extract_location(query)
            crop = self._extract_crop(query)
            
            # Force agricultural data fetching for any crop/farming query
            agricultural_keywords = ['crop', 'grow', 'farm', 'agriculture', 'plant', 'cultivation', 'harvest', 'seed', 'market', 'price', 'profit', 'yield']
            is_agricultural_query = any(keyword in query.lower() for keyword in agricultural_keywords)
            
            if is_agricultural_query:
                # Pre-fetch agricultural data to ensure it's included
                try:
                    agri_data = await get_agricultural_data(location=location, crop=crop)
                    enhanced_query = f"""Based on this agricultural data from data.gov.in:

{agri_data}

Now answer the user's question: {query}

IMPORTANT: Use the above data in your response. Provide specific recommendations based on the market prices and trends shown."""
                    input_data = {"input": enhanced_query}
                except Exception as e:
                    logger.error(f"Error pre-fetching agricultural data: {e}")
                    input_data = {"input": query}
            else:
                input_data = {"input": query}
            
            # If image is provided, modify query to include image analysis
            if image_data:
                input_data["input"] = f"Please analyze this image: {query}"
            
            # Add context if available
            if context:
                context_str = self._format_context(context)
                input_data["input"] = f"Context: {context_str}\n\nQuery: {input_data['input']}"
            
            # Execute agent
            response = await self.agent_executor.ainvoke(input_data)
            
            return response.get("output", "I apologize, but I couldn't generate a response. Please try again.")
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"Error processing your query: {str(e)}"

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context data for the agent"""
        formatted = []
        
        if "market_data" in context:
            formatted.append(f"Market Data: {context['market_data']}")
        
        if "weather_data" in context:
            formatted.append(f"Weather Data: {context['weather_data']}")
        
        if "location" in context:
            formatted.append(f"Location: {context['location']}")
        
        if "crop" in context:
            formatted.append(f"Crop: {context['crop']}")
        
        return "\n".join(formatted) if formatted else ""

    def _extract_location(self, query: str) -> Optional[str]:
        """Extract location from user query"""
        query_lower = query.lower()
        
        # Common Indian states and regions
        locations = [
            'telangana', 'andhra pradesh', 'punjab', 'haryana', 'maharashtra', 
            'gujarat', 'rajasthan', 'uttar pradesh', 'bihar', 'west bengal',
            'tamil nadu', 'karnataka', 'kerala', 'odisha', 'jharkhand',
            'chhattisgarh', 'madhya pradesh', 'assam', 'himachal pradesh'
        ]
        
        for location in locations:
            if location in query_lower:
                return location.title()
        
        return None
    
    def _extract_crop(self, query: str) -> Optional[str]:
        """Extract crop from user query"""
        query_lower = query.lower()
        
        # Common crops
        crops = [
            'rice', 'wheat', 'cotton', 'sugarcane', 'maize', 'bajra', 'jowar',
            'pulses', 'gram', 'arhar', 'moong', 'urad', 'groundnut', 'soybean',
            'mustard', 'sunflower', 'sesame', 'castor', 'jute', 'tea', 'coffee',
            'coconut', 'arecanut', 'cardamom', 'pepper', 'turmeric', 'ginger',
            'onion', 'potato', 'tomato', 'chilli', 'garlic', 'coriander'
        ]
        
        for crop in crops:
            if crop in query_lower:
                return crop.title()
        
        return None

    def analyze_image_with_text(self, image_data: str, text_query: str) -> str:
        """Analyze image with accompanying text query"""
        try:
            # Use the image analysis tool directly
            image_tool = ImageAnalysisTool(self.llm)
            return image_tool._run(image_data, text_query)
        except Exception as e:
            logger.error(f"Error in image analysis: {e}")
            return f"Error analyzing image: {str(e)}"

# Factory function to create agent instance
def create_kisangpt_agent(gemini_api_key: str) -> KisanGPTLangChainAgent:
    """Create and return a KisanGPT LangChain agent instance"""
    return KisanGPTLangChainAgent(gemini_api_key)
