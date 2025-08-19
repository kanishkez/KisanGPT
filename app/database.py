from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import settings

# Create database engine
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

class User(Base):
    """User model for storing farmer information"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)
    location = Column(String, nullable=True)
    language = Column(String, default="hi")  # Default to Hindi
    crops_grown = Column(Text, nullable=True)  # JSON string of crops
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Conversation(Base):
    """Conversation model for storing chat history"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    message = Column(Text)
    response = Column(Text)
    message_type = Column(String, default="text")  # text, voice, image
    created_at = Column(DateTime, default=datetime.utcnow)

class WeatherCache(Base):
    """Weather cache model for storing weather data"""
    __tablename__ = "weather_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String, index=True)
    weather_data = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

class MarketPrice(Base):
    """Market price model for storing crop prices"""
    __tablename__ = "market_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    crop = Column(String, index=True)
    mandi = Column(String, index=True)
    price_min = Column(Integer)
    price_max = Column(Integer)
    unit = Column(String, default="quintal")
    date = Column(DateTime, default=datetime.utcnow)
    source = Column(String)

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 