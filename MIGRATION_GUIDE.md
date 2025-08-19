# KisanGPT Migration Guide: Groq to LangChain + Gemini 2.5 Pro

## Overview

This guide documents the migration of KisanGPT from a Groq-based architecture to a LangChain-based system powered by Google's Gemini 2.5 Pro. The new architecture provides enhanced image analysis capabilities while maintaining all existing functionality.

## Key Changes

### 1. **AI Model Migration**
- **Before**: Groq with Llama 3.1 70B
- **After**: Google Gemini 2.5 Pro via LangChain
- **Benefits**: 
  - Multi-modal capabilities (text + image analysis)
  - Better agricultural domain understanding
  - More reliable API availability

### 2. **New Image Analysis Features**
- Upload crop images for disease/pest identification
- Plant health assessment
- Visual crop classification
- Integrated with text-based recommendations

### 3. **Architecture Changes**
- **LangChain Agent**: `app/services/langchain_agent.py`
- **Custom Tools**: Data.gov.in integration, image analysis
- **Enhanced Frontend**: Image upload, API key management

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key for configuration

### 3. Environment Configuration
Copy `env.example` to `.env` and update:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here
DATAGOV_API_KEY=579b464db66ec23bdd000001b19d189b5ea74357629a8302e0ed3372

# Application
APP_NAME=KisanGPT
APP_VERSION=2.0.0
MODEL_NAME=gemini-2.0-flash-exp
```

### 4. Run the Application
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## New Features

### 1. **Image Analysis**
- **Endpoint**: `POST /api/chat-with-image`
- **Supports**: JPG, PNG, WebP, GIF
- **Use Cases**:
  - Crop disease identification
  - Pest detection
  - Plant health assessment
  - Growth stage analysis

### 2. **Enhanced Chat Interface**
- **API Key Input**: Users can enter their own Gemini API key
- **Image Upload**: Camera button for image selection
- **Preview**: Image preview before sending
- **Multi-modal**: Combined text + image queries

### 3. **LangChain Tools**
- **DataGovTool**: Fetches market prices and crop data
- **ImageAnalysisTool**: Processes agricultural images
- **Context Integration**: Combines multiple data sources

## API Endpoints

### Text Chat
```http
POST /api/chat
Content-Type: application/json

{
  "message": "What crops should I grow in Punjab?",
  "location": "Punjab",
  "session_id": "optional-session-id",
  "gemini_api_key": "optional-api-key"
}
```

### Image + Text Chat
```http
POST /api/chat-with-image
Content-Type: multipart/form-data

message: "What disease is affecting my crop?"
image: [image file]
location: "Punjab"
session_id: "optional-session-id"
gemini_api_key: "optional-api-key"
```

## Frontend Changes

### 1. **New UI Elements**
- API key input section in header
- Image upload button (📷)
- Image preview with remove option
- Enhanced feature grid

### 2. **JavaScript Updates**
- Image handling functions
- API key management
- Multi-modal request handling
- Local storage for API key

### 3. **CSS Enhancements**
- Responsive header layout
- Image preview styling
- API key section styling
- Mobile-friendly design

## Data Flow

### Text-Only Query
```
User Input → NLP Analysis → Context Gathering → LangChain Agent → Gemini 2.5 Pro → Response
```

### Image + Text Query
```
User Input + Image → Image Analysis Tool → Gemini Vision → Combined with Text Analysis → Response
```

## Migration Checklist

- [x] Update dependencies in `requirements.txt`
- [x] Create LangChain agent service
- [x] Implement image analysis capabilities
- [x] Update frontend for image upload
- [x] Add API key management
- [x] Update configuration files
- [x] Remove deprecated Groq dependencies
- [x] Update environment example
- [x] Test image classification functionality

## Example Usage

### 1. **Crop Recommendation**
```
User: "What crops should I grow in Maharashtra?"
Response: Detailed recommendations based on soil, climate, and market data
```

### 2. **Disease Identification**
```
User: [Uploads image of diseased plant] "What's wrong with my tomato plant?"
Response: Disease identification, treatment recommendations, prevention tips
```

### 3. **Market Analysis**
```
User: "Current wheat prices in Punjab"
Response: Real-time market data from data.gov.in with analysis
```

## Troubleshooting

### Common Issues

1. **API Key Error**
   - Ensure valid Gemini API key is provided
   - Check API key permissions in Google AI Studio

2. **Image Upload Issues**
   - Verify image format (JPG, PNG, WebP, GIF)
   - Check file size limits
   - Ensure stable internet connection

3. **LangChain Errors**
   - Verify all dependencies are installed
   - Check Python version compatibility (3.8+)

### Performance Tips

1. **Image Optimization**
   - Resize large images before upload
   - Use compressed formats when possible

2. **API Usage**
   - Implement rate limiting for production
   - Cache responses for repeated queries

## Security Considerations

1. **API Key Storage**
   - Keys stored in browser localStorage
   - Server-side validation required
   - Consider encrypted storage for production

2. **Image Processing**
   - Validate image types and sizes
   - Implement virus scanning for production
   - Consider image compression

## Future Enhancements

1. **Advanced Features**
   - Batch image processing
   - GPS-based location detection
   - Weather integration with image analysis

2. **Performance**
   - Response caching
   - Image preprocessing
   - CDN for static assets

3. **Analytics**
   - Usage tracking
   - Performance monitoring
   - User feedback collection

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review API documentation
3. Verify environment configuration
4. Test with sample images and queries

---

**Migration completed successfully!** 🌾

The new KisanGPT now provides enhanced agricultural assistance with powerful image analysis capabilities while maintaining all existing functionality.
