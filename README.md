# KisanGPT - Agricultural Assistant

An intelligent agricultural assistant that helps farmers make informed decisions about crops, market prices, pest management, and government schemes. Built with Google Gemini 2.5 Pro for comprehensive agricultural knowledge.

## Features

### Core Capabilities
- **AI-Powered Q&A**: Advanced agricultural knowledge and recommendations
- **Market Intelligence**: Real-time market prices and trends from government data sources
- **Image Analysis**: Pest and disease identification from crop photos
- **Crop Recommendations**: Region-specific suggestions with profitability analysis
- **Government Schemes**: Information about agricultural subsidies and programs
- **Weather Advisory**: Weather-based farming recommendations
- **Profit Analysis**: Market price categorization and optimization insights

### Technical Features
- Multi-modal interface supporting both text and image inputs
- Session management with conversation history
- Optimized performance with smart query detection
- Clean, responsive web interface with drag-and-drop support

Demos:
<img width="1200" height="692" alt="image" src="https://github.com/user-attachments/assets/94c97d64-e99e-40f1-a5c7-33c5e72cc0ce" />

<img width="1183" height="945" alt="image" src="https://github.com/user-attachments/assets/3ed4a0c8-b2a9-4922-bd5d-5cb7b43afd66" />




## Technology Stack

- **Backend**: FastAPI with Python 3.8+
- **AI Integration**: Google Gemini 2.5 Pro
- **Data Sources**: data.gov.in APIs for agricultural market data
- **Frontend**: HTML5, CSS3, JavaScript
- **Image Processing**: Pillow library

## Installation

1. Clone the repository:
```bash
git clone https://github.com/kanishkez/KisanGPT.git
cd KisanGPT
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp env.example .env
# Edit .env file with your API keys
```

5. Start the application:
```bash
# Method 1: Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Method 2: Using Python module (recommended)
PYTHONPATH=. python3 app/main.py
```

Access the application at `http://localhost:8000`

## Configuration

Create a `.env` file in the root directory:

```
GEMINI_API_KEY=your_gemini_api_key
DATAGOV_API_KEY=your_datagov_api_key
APP_NAME=KisanGPT
APP_VERSION=1.0.0
```

## API Documentation

### Endpoints

- `GET /` - Main application interface
- `POST /api/chat` - Process text-based agricultural queries
- `POST /api/chat-with-image` - Analyze images for pest/disease identification
- `GET /api/config` - Retrieve application configuration

### Usage Examples

**Text Queries:**
- "What crops should I grow in Punjab during winter season?"
- "Current market prices for wheat in Maharashtra"
- "Information about PM-KISAN scheme eligibility criteria"
- "Best farming practices for increasing yield in rice"
- "Weather-based farming advice for this season"

**Image Analysis:**
- Upload crop photos for pest identification (supports JPG, PNG, GIF, WebP)
- Disease diagnosis with treatment recommendations
- Nutrient deficiency detection and solutions
- Drag & drop or paste images directly into the chat interface

## Project Structure

```
KisanGPT/
├── app/
│   ├── config.py              # Application configuration
│   ├── main.py                # FastAPI application entry point
│   ├── models/
│   │   └── schemas.py         # Data models and schemas
│   ├── services/
│   │   ├── agricultural_data.py    # Market data service
│   │   ├── langchain_agent.py      # AI agent implementation
│   │   └── ...
│   ├── utils/
│   │   └── helpers.py         # Utility functions
│   └── web/
│       └── static/            # Frontend assets
├── data/                      # Data storage directory
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # Project documentation
```

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Quality
```bash
# Format code
black app/

# Check linting
flake8 app/
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and commit: `git commit -m 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Acknowledgments

- Google Gemini AI for language processing capabilities
- Data.gov.in for providing agricultural market data APIs
- FastAPI framework for the backend infrastructure
- The agricultural community for valuable feedback and requirements



