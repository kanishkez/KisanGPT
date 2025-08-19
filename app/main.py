import logging
import re
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import uuid
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import base64
from PIL import Image
import io
from app.config import settings
from app.services.agricultural_data import AgriculturalDataService
from app.utils.helpers import extract_location_and_crop
import google.generativeai as genai
from app.services.market_service import MarketService
from app.services.news_service import NewsService
from app.services.nlp_service import NLPService
# (helpers imported above)

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="KisanGPT - Your Agricultural Assistant"
)

# Initialize services
market_service = MarketService()
news_service = NewsService()
nlp_service = NLPService()

# Global agent instance - will be initialized when API key is provided
langchain_agent = None

# In-memory conversation storage (in production, use Redis or database)
conversations: Dict[str, List[Dict]] = {}

# Add CORS middleware to handle encoding properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

# Dev middleware: prevent caching of static/index so UI updates reflect immediately on restart
@app.middleware("http")
async def no_cache_static(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

class ChatRequest(BaseModel):
    message: str
    location: Optional[str] = None
    crop: Optional[str] = None
    session_id: Optional[str] = None
    gemini_api_key: Optional[str] = None
    conversation_history: Optional[List[dict]] = None
    debug_return_context: Optional[bool] = False

class ImageChatRequest(BaseModel):
    message: str
    location: Optional[str] = None
    session_id: Optional[str] = None
    gemini_api_key: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class VoiceChatRequest(BaseModel):
    transcript: str
    session_id: Optional[str] = None
    conversation_history: Optional[List[dict]] = None
    gemini_api_key: Optional[str] = None

class VoiceChatResponse(BaseModel):
    response: str
    session_id: str

@app.get("/test-session")
async def test_session():
    """Test endpoint to verify session generation"""
    session_id = get_or_create_session()
    return {"session_id": session_id, "message": "Session created successfully"}

@app.get("/api/config")
async def get_config():
    """Get frontend configuration"""
    return {
        "has_api_key": bool(settings.GEMINI_API_KEY),
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION
    }

@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("app/web/static/index.html")

def get_or_create_session(session_id: Optional[str] = None) -> str:
    """Get existing session or create new one"""
    if not session_id or session_id not in conversations:
        session_id = str(uuid.uuid4())
        conversations[session_id] = []
    return session_id

def sanitize_ai_response(text: str) -> str:
    """Remove self-referential/meta lines like 'I will answer in English' or signatures.
    Keeps core content intact.
    """
    if not text:
        return text

    patterns = [
        r"(?im)^\s*I\s+(will|shall)\s+(answer|respond)\s+(in|using)\s+[^\n\.]+[\.!]?\s*$",
        r"(?im)^\s*I\s+(will|shall)\s+(answer|respond)\s+as\s+KisanGPT[^\n]*$",
        r"(?im)^\s*As\s+(an\s+AI|KisanGPT)[^\n]*$",
        r"(?im)^\s*(I|We)\s+(will|shall)\s+(provide|give)\s+[^\n]*$",
        r"(?im)^\s*—\s*KisanGPT\s*$",
        # Remove inaccurate data access disclaimers
        r"(?im)^.*(due to current issues retrieving real[- ]?time|I (do not|don't) have real[- ]?time access|cannot retrieve real[- ]?time|no real[- ]?time access).*$",
        r"(?im)^.*(please check (your|the) local (market|mandi)|check your local agricultural market).*$",
    ]
    for p in patterns:
        text = re.sub(p, "", text)

    # Remove in-line sentences like 'I will answer in English.' and real-time disclaimers inside paragraphs
    text = re.sub(r"(?i)\bI\s+(will|shall)\s+(answer|respond)\s+(in|using)\s+[^\.\n]+\.\s*", "", text)
    text = re.sub(r"(?i)(due to current issues retrieving real[- ]?time|I (do not|don't) have real[- ]?time access|cannot retrieve real[- ]?time|no real[- ]?time access)[^\.\n]*\.\s*", "", text)
    text = re.sub(r"(?i)please check (your|the) local (market|mandi)[^\.\n]*\.\s*", "", text)

    # Collapse excessive blank lines and trim
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text

def detect_target_language_name(text: str) -> str:
    """Very lightweight language hint based on script blocks in the user's message.
    Returns a human-readable language name used in the prompt rule.
    Defaults to 'English' for ASCII/mixed.
    """
    if not text:
        return "English"
    # Unicode ranges for major Indian scripts
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi"
    if re.search(r"[\u0A80-\u0AFF]", text):
        return "Gujarati"
    if re.search(r"[\u0A00-\u0A7F]", text):
        return "Punjabi"
    if re.search(r"[\u0980-\u09FF]", text):
        return "Bengali"
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "Kannada"
    if re.search(r"[\u0C00-\u0C7F]", text):
        return "Telugu"
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "Tamil"
    if re.search(r"[\u0900-\u097F]", text) and "marathi" in text.lower():
        return "Marathi"
    # Fallback
    return "English"

def add_to_conversation(session_id: str, role: str, content: str):
    """Add message to conversation history"""
    if session_id not in conversations:
        conversations[session_id] = []
    
    conversations[session_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now()
    })
    
    # Keep only last 10 messages to prevent context from getting too long
    if len(conversations[session_id]) > 10:
        conversations[session_id] = conversations[session_id][-10:]

def get_conversation_context(session_id: str) -> str:
    """Get conversation history as context"""
    if session_id not in conversations:
        return ""
    
    context_parts = []
    for msg in conversations[session_id][-6:]:  # Last 6 messages
        if msg["role"] == "user":
            context_parts.append(f"User: {msg['content']}")
        elif msg["role"] == "assistant":
            context_parts.append(f"Assistant: {msg['content']}")
    
    return "\n".join(context_parts)

def get_agent(gemini_api_key: str):
    """Get or create LangChain agent instance"""
    global langchain_agent
    try:
        if not langchain_agent or langchain_agent.gemini_api_key != gemini_api_key:
            langchain_agent = create_kisangpt_agent(gemini_api_key)
        return langchain_agent
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=400, detail=f"Error initializing AI agent: {str(e)}")

@app.post("/api/voice-chat")
async def voice_chat(request: VoiceChatRequest):
    """Voice chat endpoint: takes transcript, adds data.gov.in context, and answers in same language."""
    try:
        session_id = request.session_id or str(uuid.uuid4())

        # Use environment API key if available, otherwise provided
        api_key = settings.GEMINI_API_KEY or request.gemini_api_key
        if not api_key:
            raise HTTPException(status_code=400, detail="Gemini API key is required")

        # Configure Gemini
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(settings.MODEL_NAME)

        # Build context: live weather (OpenWeather) and market data when relevant
        message_lower = request.transcript.lower()
        market_keywords = ['crop', 'grow', 'market', 'price', 'profit', 'cultivation', 'farming', 'बेचना', 'कीमत']
        is_market_query = any(k in message_lower for k in market_keywords)

        agri_service = AgriculturalDataService()
        location, crop = extract_location_and_crop(request.transcript)
        logger.info(f"[voice-chat] market_query={is_market_query} location='{location}' crop='{crop}'")

        context_parts = []
        # Always attempt live weather if we have a location and key
        weather_md = await agri_service.get_openweather_summary(location)
        if weather_md:
            context_parts.append(weather_md)
        if weather_md:
            logger.info(f"[voice-chat] added weather context: {len(weather_md)} chars")
        # Market context only if market-like query
        if is_market_query:
            market_data = await agri_service.get_market_prices_optimized(location=location, crop=crop)
            if market_data:
                logger.info(f"[voice-chat] added market context: {len(market_data)} chars")
                context_parts.append(market_data)
        context_data = "\n\n".join(context_parts)

        # Conversation context
        conversation_context = ""
        # If a location is detected in the current transcript, skip prior conversation to prevent region mixing
        if not location and request.conversation_history:
            conversation_context = "\n\nPrevious Conversation:\n"
            for msg in request.conversation_history[-5:]:
                role = "Farmer" if msg.get("who") == "user" else "KisanGPT"
                conversation_context += f"{role}: {msg.get('text', '')}\n"

        # System prompt: direct answers, no self-reference, strict same language as current user message
        target_language = detect_target_language_name(request.transcript)
        system_prompt = f"""Role: Multilingual agricultural assistant for Indian farmers.

Style and Tone:
- Detect the farmer's language and answer in that language.
- Speak directly to the farmer. Do NOT say phrases like "I will answer as KisanGPT", "as an AI", or any self-references.
- Be practical, concise, and respectful. Avoid meta commentary and disclaimers.
 - Do NOT announce the language you are using (e.g., no "I will answer in English/Hindi"). Start directly with the content.

Hard Rule:
- Target Language: {target_language}. Respond strictly in this language. Ignore the languages used in previous messages.
- Region Lock: Use data and examples ONLY for this region: {location or 'India'}. Do NOT mention or switch to other states/regions (e.g., if region is Haryana, do not mention Punjab). If previous conversation suggests a different region, ignore it.

No-Disclaimers:
- You DO have access to government market data via the provided context blocks. Never claim lack of real-time access. If market context is missing, provide a concise fallback using regional crop recommendations and practical steps, and ask the farmer to specify the state and commodity for precise prices. Do not add generic disclaimers like "check your local market".

Content Requirements:
- Use the provided context (weather/market) when relevant and cite numbers with units (°C, mm, kg/ha, L/acre, etc.).
- Prefer short sections and bullet points. Keep it scannable.

Response Structure:
1) Clear title with crop/topic.
2) Weather summary (only if provided).
3) Detailed guidance with reasons and numbers.
4) Actionable steps (4–8 concise bullets).
5) Safety/caution notes.
6) Localized tip if possible.

Context Data:
{context_data}
{conversation_context}
"""

        response = model.generate_content(
            f"{system_prompt}\n\nFarmer's Question (transcript): {request.transcript}"
        )

        cleaned = sanitize_ai_response(response.text)
        return VoiceChatResponse(response=cleaned, session_id=session_id)

    except Exception as e:
        logger.error(f"Error in voice chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing voice chat: {str(e)}")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Process comprehensive agricultural queries with Gemini AI"""
    try:
        session_id = request.session_id or str(uuid.uuid4())

        # Use environment API key if available, otherwise use provided key
        api_key = settings.GEMINI_API_KEY or request.gemini_api_key
        # Only configure Gemini if we are not in debug_return_context mode
        model = None
        if not request.debug_return_context:
            if not api_key:
                raise HTTPException(status_code=400, detail="Gemini API key is required")
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(settings.MODEL_NAME)

        # Build context from services (OpenWeather + market if relevant)
        msg_lower = (request.message or "").lower()
        market_keywords = ['crop', 'grow', 'market', 'price', 'profit', 'cultivation', 'farming', 'बेचना', 'कीमत']
        is_market_query = any(k in msg_lower for k in market_keywords)

        agri_service = AgriculturalDataService()
        inferred_location, inferred_crop = extract_location_and_crop(request.message or "")
        # Prioritize explicit request fields over inference
        location = (request.location or None) or inferred_location
        crop = (request.crop or None) or inferred_crop
        logger.info(f"[chat] market_query={is_market_query} location='{location}' crop='{crop}'")

        context_parts: List[str] = []
        weather_md = await agri_service.get_openweather_summary(location)
        if weather_md:
            context_parts.append(weather_md)
        if weather_md:
            logger.info(f"[chat] added weather context: {len(weather_md)} chars")
        if is_market_query:
            market_info = await agri_service.get_market_prices_optimized(location=location, crop=crop)
            # Only add market context if it's not the 'no data' fallback message.
            # The system prompt is better equipped to handle the no-data case gracefully.
            if market_info and "No recent market records" not in market_info:
                logger.info(f"[chat] added market context: {len(market_info)} chars")
                context_parts.append(market_info)

        # Add regional crop recommendations to context to enforce region lock
        if location:
            regional_recos = get_regional_crop_recommendations(location)
            if regional_recos:
                logger.info(f"[chat] added regional recommendations: {len(regional_recos)} chars")
                context_parts.append(regional_recos)
        context_data = "\n\n".join(context_parts)

        # Conversation context from server memory
        # If a location is provided/detected for this request, ignore prior context to avoid cross-region bleed
        conversation_context = ""
        if not location:
            conversation_context = get_conversation_context(session_id)

        # If debug flag is on, return the assembled context for verification and skip model call
        if request.debug_return_context:
            preview = context_data or ""
            if not preview:
                preview = "<no-context>"
            return ChatResponse(response=preview, session_id=session_id)

        # System prompt: direct answers, no self-reference, strict same language as current user message
        target_language = detect_target_language_name(request.message or "")
        region_focus = (location or "India")
        system_prompt = f"""Role: Multilingual agricultural assistant for Indian farmers.

Style and Tone:
- Detect the farmer's language and answer in that language.
- Do NOT include any self-reference (no "I will answer as KisanGPT", "as an AI", etc.).
- Practical, concise, respectful; avoid meta commentary.
 - Do NOT announce the language; start with the content immediately.

Hard Rule:
- Target Language: {target_language}. Respond strictly in this language. Ignore languages used in earlier conversation turns.
- Region Focus: {region_focus}. Use market and agronomic context for this region only. Do not switch to other states/regions unless user changes it explicitly.

No-Disclaimers:
- You DO have access to government market data via the provided context blocks. Never claim lack of real-time access. If market context is missing, give a concise fallback using regional recommendations and actionable guidance, and ask the farmer to specify the state and commodity for exact prices. Avoid generic advice like "check your local market".

Content Requirements:
- Use the provided context (weather/market) when relevant and include numbers with units (°C, mm, kg/ha, L/acre, etc.).
- Prefer short sections and bullet points.

Response Structure:
1) Title with crop/topic.
2) Weather summary (only if provided).
3) Detailed guidance with reasons and numbers.
4) Actionable steps (4–8 concise bullets).
5) Safety/caution notes.
6) Localized tip if possible.

Context Data:
{context_data}

Previous Conversation:
{conversation_context}
"""

        # Add user message to conversation memory
        add_to_conversation(session_id, "user", request.message)

        # Generate response with Gemini
        response = model.generate_content(
            f"{system_prompt}\n\nFarmer's Question: {request.message}"
        )

        # Save assistant response (sanitized)
        cleaned = sanitize_ai_response(response.text)
        add_to_conversation(session_id, "assistant", cleaned)

        return ChatResponse(response=cleaned, session_id=session_id)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@app.post("/api/chat-with-image")
async def chat_with_image_endpoint(
    message: str = Form(...),
    image: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    """Handle agricultural image analysis for pest/disease identification"""
    try:
        session_id = session_id or str(uuid.uuid4())
        
        # Use environment API key if available
        gemini_api_key = settings.GEMINI_API_KEY or api_key
        if not gemini_api_key:
            raise HTTPException(status_code=400, detail="Gemini API key is required")
        
        # Read and encode image
        image_data = await image.read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Configure Gemini for vision
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Enhanced system prompt for image analysis (no self-reference, multilingual)
        system_prompt = """Role: Agricultural assistant specializing in crop health image analysis.

Style and Tone:
- Detect the farmer's language and answer in that language.
- Do NOT include self-referential phrases or signatures. Answer directly.
 - Do NOT announce the language; start with the content immediately.

Capabilities:
- Pest identification and treatment recommendations
- Disease diagnosis and management
- Nutrient deficiency detection
- Weed identification and control methods
- Crop health assessment and growth stage evaluation

Instructions:
1) Analyze the uploaded image carefully.
2) Identify likely issues (pest/disease/deficiency/other).
3) Provide treatment with: chemical names, dosages, application method and timing, preventive measures, and organic alternatives when available.
4) Include relevant government scheme info when appropriate.
5) Be practical and immediately actionable.

Response Format:
🔍 Image Analysis:
[What you see]

⚠️ Issue Identified:
[Name]

💊 Treatment Recommendations:
[Specific treatments with dosages]

🛡️ Prevention:
[Prevention steps]

📋 Additional Notes:
[Any relevant schemes, timing, or tips]
"""

        # Prepare image for Gemini
        import PIL.Image
        import io
        
        pil_image = PIL.Image.open(io.BytesIO(image_data))
        
        # Generate response with image analysis
        response = model.generate_content([
            system_prompt + f"\n\nFarmer's Question: {message}",
            pil_image
        ])
        
        cleaned = sanitize_ai_response(response.text)
        return ChatResponse(
            response=cleaned,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error in image chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

def get_sowing_season(crop: str) -> str:
    """Get sowing season for a crop"""
    seasons = {
        "rice": "June-July (Kharif season)",
        "wheat": "October-November (Rabi season)",
        "cotton": "April-May (Summer season)",
        "sugarcane": "February-March",
        "maize": "June-July (Kharif) or October-November (Rabi)",
        "pulses": "June-July (Kharif) or October-November (Rabi)",
        "oilseeds": "June-July (Kharif) or October-November (Rabi)",
        "vegetables": "Year-round depending on variety",
        "fruits": "Varies by fruit type and region"
    }
    return seasons.get(crop.lower(), "Please consult local agricultural office for specific sowing times")

def get_soil_requirements(crop: str) -> str:
    """Get soil requirements for a crop"""
    soils = {
        "rice": "Clay or clay loam soil with good water retention",
        "wheat": "Well-drained loamy soil",
        "cotton": "Deep, well-drained black cotton soil or alluvial soil",
        "sugarcane": "Deep, well-drained loam or clay loam soil",
        "maize": "Well-drained loamy soil rich in organic matter",
        "pulses": "Well-drained loamy soil",
        "oilseeds": "Well-drained sandy loam to clay loam soil",
        "vegetables": "Rich, well-drained loamy soil",
        "fruits": "Well-drained soil with good organic matter"
    }
    return soils.get(crop.lower(), "Consult local agricultural experts for soil recommendations")

def get_water_needs(crop: str) -> str:
    """Get water requirements for a crop"""
    water = {
        "rice": "Continuous flooding or regular irrigation",
        "wheat": "5-6 irrigations during the growing season",
        "cotton": "Regular irrigation every 15-20 days",
        "sugarcane": "Regular irrigation with proper drainage",
        "maize": "Regular irrigation, especially during tasseling",
        "pulses": "Moderate irrigation, drought-tolerant varieties available",
        "oilseeds": "Moderate irrigation, avoid waterlogging",
        "vegetables": "Regular irrigation, varies by vegetable type",
        "fruits": "Regular irrigation, avoid waterlogging"
    }
    return water.get(crop.lower(), "Water needs vary by season and local conditions")

def get_common_diseases(crop: str) -> str:
    """Get common diseases for a crop"""
    diseases = {
        "rice": "Blast, Bacterial leaf blight, Sheath blight",
        "wheat": "Rust, Loose smut, Powdery mildew",
        "cotton": "Wilt, Root rot, Leaf curl virus",
        "sugarcane": "Red rot, Smut, Wilt",
        "maize": "Leaf blight, Stalk rot, Rust",
        "pulses": "Wilt, Root rot, Powdery mildew",
        "oilseeds": "Alternaria blight, Sclerotinia rot",
        "vegetables": "Varies by vegetable, common: blight, wilt, rot",
        "fruits": "Varies by fruit, common: scab, rot, powdery mildew"
    }
    return diseases.get(crop.lower(), "Monitor crop regularly and consult experts if you notice any issues")

def get_regional_crop_recommendations(location: str) -> str:
    """Get regional crop recommendations"""
    recommendations = {
        "Punjab": ["Wheat", "Rice", "Cotton", "Maize", "Sugarcane"],
        "Haryana": ["Wheat", "Rice", "Sugarcane", "Cotton", "Oilseeds"],
        "Uttar Pradesh": ["Wheat", "Rice", "Sugarcane", "Potato", "Pulses"],
        "Bihar": ["Rice", "Wheat", "Maize", "Pulses", "Oilseeds"],
        "West Bengal": ["Rice", "Jute", "Tea", "Potato", "Vegetables"],
        "Madhya Pradesh": ["Soybean", "Wheat", "Rice", "Pulses", "Cotton"],
        "Gujarat": ["Cotton", "Groundnut", "Wheat", "Rice", "Bajra"],
        "Maharashtra": ["Cotton", "Jowar", "Sugarcane", "Rice", "Pulses"],
        "Karnataka": ["Rice", "Ragi", "Jowar", "Cotton", "Sugarcane"],
        "Andhra Pradesh": ["Rice", "Cotton", "Sugarcane", "Chillies", "Turmeric"],
        "Telangana": ["Rice", "Cotton", "Maize", "Pulses", "Chillies"],
        "Tamil Nadu": ["Rice", "Sugarcane", "Coconut", "Cotton", "Groundnut"],
        "Kerala": ["Rice", "Coconut", "Rubber", "Spices", "Tea"],
        "Rajasthan": ["Wheat", "Bajra", "Pulses", "Oilseeds", "Cotton"],
        "Odisha": ["Rice", "Pulses", "Oilseeds", "Jute", "Sugarcane"]
    }
    
    location_title = location.title()
    if location_title in recommendations:
        crops = recommendations[location_title]
        return "**Recommended crops for this region:**\n" + "\n".join([f"- {crop}" for crop in crops])
    else:
        return ("**Common crops grown in India:**\n"
                "- Rice (Kharif season)\n"
                "- Wheat (Rabi season)\n"
                "- Pulses (Year-round)\n"
                "- Oilseeds (Season varies)\n"
                "- Cotton (Kharif season)")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
