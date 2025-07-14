# OpenProject Haystack

This project is an AI-powered application using [Haystack](https://github.com/deepset-ai/haystack) and [Ollama](https://ollama.ai/) for natural language processing. The project follows standard Haystack conventions and is containerized with Docker for both development and deployment.

## Stack
- Python 3.11
- Haystack AI (for NLP pipelines)
- FastAPI (for API endpoints)
- Ollama (for local LLM inference)
- Docker & Docker Compose (for reproducible environments)

## Project Structure
```
openproject-haystack/
├── README.md
├── requirements.txt
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── config/
│   └── settings.py          # Configuration management
├── src/
│   ├── main.py             # FastAPI application entry point
│   ├── api/
│   │   └── routes.py       # API endpoints
│   ├── pipelines/
│   │   └── generation.py   # Haystack pipeline definitions
│   └── models/
│       └── schemas.py      # Pydantic models
└── tests/                  # Test modules
```

## Getting Started

### Development with Docker Compose
```bash
# Start the services
docker-compose up --build

# The API will be available at http://localhost:8000
# Health check: GET http://localhost:8000/health
# Text generation: POST http://localhost:8000/generate
```

### API Endpoints
- `GET /health` - Health check endpoint
- `POST /generate` - Generate text from a prompt

### Configuration
Environment variables can be set to customize the application:
- `OLLAMA_URL` - Ollama service URL (default: http://ollama:11434)
- `OLLAMA_MODEL` - Model to use (default: mistral:latest)
- `GENERATION_NUM_PREDICT` - Max tokens to generate (default: 1000)
- `GENERATION_TEMPERATURE` - Generation temperature (default: 0.7)
