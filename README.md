# OpenProject Haystack

This project is an AI-powered application using [Haystack](https://github.com/deepset-ai/haystack) and [Ollama](https://ollama.ai/) for natural language processing. The project follows standard Haystack conventions and is containerized with Docker for both development and deployment.

**NEW**: Now includes OpenAI-compatible API endpoints for seamless integration with existing applications!

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
├── test_openai_api.py       # Test script for OpenAI API compatibility
├── config/
│   └── settings.py          # Configuration management
├── src/
│   ├── main.py             # FastAPI application entry point
│   ├── api/
│   │   └── routes.py       # API endpoints (including OpenAI-compatible)
│   ├── pipelines/
│   │   └── generation.py   # Haystack pipeline definitions
│   └── models/
│       └── schemas.py      # Pydantic models (including OpenAI schemas)
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

## API Endpoints

### Original Endpoints
- `GET /health` - Health check endpoint
- `POST /generate` - Generate text from a prompt

### OpenAI-Compatible Endpoints
- `POST /v1/chat/completions` - Chat completion (OpenAI-compatible)
- `GET /v1/models` - List available models
- `GET /v1/models/{model_id}` - Get specific model information

## OpenAI API Compatibility

This application now provides full OpenAI chat completion API compatibility, allowing you to use it as a drop-in replacement for OpenAI's API in your applications.

### Using with OpenAI Python Client

```python
from openai import OpenAI

# Point the client to your local Haystack API
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy-key"  # Not used but required by client
)

# Use exactly like OpenAI's API
response = client.chat.completions.create(
    model="mistral:latest",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello! How are you?"}
    ],
    temperature=0.7,
    max_tokens=150
)

print(response.choices[0].message.content)
```

### Using with Direct HTTP Requests

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral:latest",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is the capital of France?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

### Supported Parameters

The chat completion endpoint supports the following OpenAI-compatible parameters:
- `model` - Model to use (maps to your Ollama models)
- `messages` - Array of message objects with `role` and `content`
- `temperature` - Controls randomness (0.0 to 2.0)
- `max_tokens` - Maximum tokens to generate
- `top_p` - Nucleus sampling parameter
- `frequency_penalty` - Frequency penalty (-2.0 to 2.0)
- `presence_penalty` - Presence penalty (-2.0 to 2.0)
- `stop` - Stop sequences
- `stream` - Streaming support (planned)

### Testing the API

Run the included test script to verify the OpenAI compatibility:

```bash
# Install test dependencies
pip install requests

# Run the test script
python test_openai_api.py

# For full OpenAI client testing, also install:
pip install openai
```

## Configuration

Environment variables can be set to customize the application:
- `OLLAMA_URL` - Ollama service URL (default: http://ollama:11434)
- `OLLAMA_MODEL` - Model to use (default: mistral:latest)
- `GENERATION_NUM_PREDICT` - Max tokens to generate (default: 1000)
- `GENERATION_TEMPERATURE` - Generation temperature (default: 0.7)
- `API_HOST` - API host (default: 0.0.0.0)
- `API_PORT` - API port (default: 8000)

## Integration Examples

### With LangChain

```python
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(
    openai_api_base="http://localhost:8000/v1",
    openai_api_key="dummy-key",
    model_name="mistral:latest"
)
```

### With Other Applications

Any application that supports OpenAI's API can now connect to your Haystack service by simply changing the base URL to `http://localhost:8000/v1`.

## Features

- ✅ Full OpenAI chat completion API compatibility
- ✅ Multi-turn conversation support
- ✅ System, user, and assistant message roles
- ✅ Token usage tracking
- ✅ Error handling with OpenAI-compatible error format
- ✅ Model listing and information endpoints
- ✅ Configurable generation parameters
- ✅ Backward compatibility with original endpoints
- 🔄 Streaming support (planned)
- 🔄 Function calling support (planned)
