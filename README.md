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
# Start the services (models will be automatically installed)
docker-compose up --build

# The API will be available at http://localhost:8000
# Health check: GET http://localhost:8000/health
# Text generation: POST http://localhost:8000/generate
```

### Automatic Model Installation

The application now automatically installs required Ollama models during startup:

1. **Ollama Service**: Starts the Ollama server
2. **Model Initialization**: Downloads and installs required models (default: `mistral:latest`)
3. **API Service**: Starts only after models are ready

This ensures that your application always has the required models available and eliminates the "model not found" errors.

## API Endpoints

### Original Endpoints
- `GET /health` - Health check endpoint
- `POST /generate` - Generate text from a prompt

### OpenAI-Compatible Endpoints
- `POST /v1/chat/completions` - Chat completion (OpenAI-compatible)
- `GET /v1/models` - List available models
- `GET /v1/models/{model_id}` - Get specific model information

### Project Management Endpoints
- `POST /generate-project-status-report` - Generate project status report from OpenProject data

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

### Basic Configuration
- `OLLAMA_URL` - Ollama service URL (default: http://ollama:11434)
- `OLLAMA_MODEL` - Model to use (default: mistral:latest)
- `GENERATION_NUM_PREDICT` - Max tokens to generate (default: 1000)
- `GENERATION_TEMPERATURE` - Generation temperature (default: 0.7)
- `API_HOST` - API host (default: 0.0.0.0)
- `API_PORT` - API port (default: 8000)
- `LOG_LEVEL` - Logging level (default: INFO, options: DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT` - Custom log format string (optional)

### Model Management
- `MODELS_TO_PULL` - Comma-separated list of models to download during initialization (default: mistral:latest)
- `REQUIRED_MODELS` - Comma-separated list of models required for the application to start (default: mistral:latest)

### Model Configuration Examples

Create a `.env` file (see `.env.example`) to customize your setup:

```bash
# For multiple models
MODELS_TO_PULL=mistral:latest,llama2:7b,codellama:latest
REQUIRED_MODELS=mistral:latest,llama2:7b

# For development with smaller models
MODELS_TO_PULL=llama2:7b
REQUIRED_MODELS=llama2:7b
OLLAMA_MODEL=llama2:7b

# For production with specific model versions
MODELS_TO_PULL=mistral:7b-instruct-v0.2-q4_0
REQUIRED_MODELS=mistral:7b-instruct-v0.2-q4_0
OLLAMA_MODEL=mistral:7b-instruct-v0.2-q4_0
```

### Troubleshooting Model Issues

If you encounter model-related errors:

1. **Check model installation logs**:
   ```bash
   docker-compose logs ollama-init
   ```

2. **Verify models are available**:
   ```bash
   curl http://localhost:11434/api/tags
   ```

3. **Manually pull a model** (if needed):
   ```bash
   docker-compose exec ollama ollama pull mistral:latest
   ```

4. **Restart with clean volumes** (if models are corrupted):
   ```bash
   docker-compose down -v
   docker-compose up --build
   ```

## Logging

The application includes comprehensive logging that outputs to stdout, making it visible in Docker logs.

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General information about application flow
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures

### Viewing Logs

```bash
# View logs from Docker containers
docker-compose logs -f api

# View logs from a specific container
docker logs openproject-haystack-api-1

# Follow logs in real-time
docker logs -f openproject-haystack-api-1
```

### Log Format

Logs are formatted with timestamps, module names, and log levels:
```
2025-07-14 20:57:50 - src.services.openproject_client - INFO - Fetching work packages from: http://example.com/api/v3/projects/123/work_packages
2025-07-14 20:57:50 - src.services.openproject_client - INFO - Successfully fetched 5 work packages
```

### Configuring Log Level

Set the log level via environment variable:

```bash
# In docker-compose.yml
environment:
  - LOG_LEVEL=DEBUG

# Or when running Docker directly
docker run -e LOG_LEVEL=DEBUG your-image

# For local development
export LOG_LEVEL=DEBUG
python3 -m uvicorn src.main:app --reload
```

### Testing Logging

Use the included test script to verify logging configuration:

```bash
python3 test_logging.py
```

This will show you how different log levels appear and confirm that your `logger.info()` calls will be visible in Docker logs.

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

## Project Status Report Generation

This application now includes a powerful feature to generate AI-powered project status reports from OpenProject data.

### How It Works

1. **Data Fetching**: The API connects to your OpenProject instance using your API key
2. **Work Package Analysis**: Analyzes all work packages in the specified project
3. **AI Report Generation**: Uses the LLM to generate a comprehensive status report
4. **Structured Output**: Returns a professional report with insights and recommendations

### Using the Project Status Report Endpoint

```bash
curl -X POST "http://localhost:8000/generate-project-status-report" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_OPENPROJECT_API_KEY" \
  -d '{
    "project_id": "1",
    "openproject_base_url": "https://your-openproject-instance.com"
  }'
```

### Python Example

```python
import requests

response = requests.post(
    "http://localhost:8000/generate-project-status-report",
    headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer YOUR_OPENPROJECT_API_KEY"
    },
    json={
        "project_id": "1",
        "openproject_base_url": "https://your-openproject-instance.com"
    }
)

if response.status_code == 200:
    report_data = response.json()
    print(f"Project: {report_data['project_id']}")
    print(f"Work packages analyzed: {report_data['work_packages_analyzed']}")
    print(f"Report:\n{report_data['report']}")
```

### Report Features

The generated reports include:

- **Executive Summary**: Overall project health and key highlights
- **Work Package Statistics**: Completion rates, status distribution, priority breakdown
- **Team Performance**: Workload distribution and productivity insights
- **Timeline Analysis**: Overdue items, upcoming deadlines, schedule adherence
- **Risk Assessment**: Identified issues and potential blockers
- **Actionable Recommendations**: Specific steps to improve project health
- **Next Steps**: Immediate actions and medium-term planning

### Authentication & Security

- Uses OpenProject API keys for secure authentication
- API key passed via `Authorization: Bearer <token>` header
- Comprehensive error handling for authentication and permission issues
- No data caching - fresh data on every request

### Error Handling

The endpoint provides detailed error responses for various scenarios:

- **401 Unauthorized**: Invalid or missing API key
- **403 Forbidden**: Insufficient permissions for the project
- **404 Not Found**: Project ID doesn't exist
- **503 Service Unavailable**: OpenProject instance unreachable
- **500 Internal Server Error**: Report generation or other internal errors

### Testing the Project Status Report

Use the included test script:

```bash
# Update the configuration in the script first
python test_project_status_report.py
```

## Features

- ✅ Full OpenAI chat completion API compatibility
- ✅ Multi-turn conversation support
- ✅ System, user, and assistant message roles
- ✅ Token usage tracking
- ✅ Error handling with OpenAI-compatible error format
- ✅ Model listing and information endpoints
- ✅ Configurable generation parameters
- ✅ Backward compatibility with original endpoints
- ✅ **OpenProject integration for status reports**
- ✅ **AI-powered project analysis and insights**
- ✅ **Comprehensive work package analysis**
- ✅ **Professional report generation**
- 🔄 Streaming support (planned)
- 🔄 Function calling support (planned)
- 🔄 Multiple report templates (planned)
