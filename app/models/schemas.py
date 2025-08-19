from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    phone_number: str
    name: Optional[str] = None
    location: Optional[str] = None
    language: str = "hi"
    crops_grown: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    message: str
    message_type: str = "text"

class MessageCreate(MessageBase):
    user_id: int

class Message(MessageBase):
    id: int
    response: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class WeatherData(BaseModel):
    location: str
    temperature: float
    humidity: int
    description: str
    forecast: List[Dict[str, Any]] = []

class MarketPriceData(BaseModel):
    crop: str
    mandi: str
    price_min: int
    price_max: int
    unit: str = "quintal"
    date: datetime
    source: str

class NewsItem(BaseModel):
    title: str
    content: str
    source: str
    published_at: datetime
    url: Optional[str] = None

class WhatsAppMessage(BaseModel):
    From: str = Field(..., alias="From")
    Body: str
    MediaUrl0: Optional[str] = None
    NumMedia: int = 0

class ChatResponse(BaseModel):
    response: str
    context: Optional[Dict[str, Any]] = None
    language: str = "hi"

class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str 