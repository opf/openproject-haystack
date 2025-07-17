# Haystack API Deployment Guide

This guide explains how to deploy the Haystack API with nginx reverse proxy and SSL certificates.

## Problem Solved

The original issue was getting a "Not Found" error when calling:
```bash
curl -X POST "https://haystack.pmflex.one/haystack/v1/chat/completions"
```

This happened because the FastAPI application was running without the `/haystack` prefix configured, so when nginx forwarded requests from `/haystack/*` to port 8000, the application couldn't find the routes.

## Solution Implemented

1. **FastAPI Configuration**: Added `root_path="/haystack"` to the FastAPI application
2. **Nginx Configuration**: Proper reverse proxy setup with SSL
3. **Testing**: Created test scripts to verify the setup

## Files Modified

### 1. `src/main.py`
```python
app = FastAPI(
    title="OpenProject Haystack",
    description="AI-powered application using Haystack and Ollama",
    version="1.0.0",
    root_path="/haystack"  # Added this line
)
```

### 2. `test_haystack_api.py` (New)
Test script to verify all endpoints work correctly with the `/haystack` prefix.

### 3. `nginx-haystack-config.example` (New)
Complete nginx configuration example with SSL, security headers, and proper proxy settings.

## Deployment Steps

### Step 1: Update Application
The FastAPI application has been updated with the correct `root_path`. After deploying this change, restart your application:

```bash
# If using Docker
docker-compose down
docker-compose up -d

# If running directly
pkill -f "uvicorn src.main:app"
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Step 2: Configure Nginx
Use the provided `nginx-haystack-config.example` as a template for your nginx configuration:

```bash
# Copy the example configuration
sudo cp nginx-haystack-config.example /etc/nginx/sites-available/haystack.pmflex.one

# Enable the site
sudo ln -s /etc/nginx/sites-available/haystack.pmflex.one /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 3: SSL Certificate Setup
If you haven't already set up SSL certificates:

```bash
# Install certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d haystack.pmflex.one

# Verify auto-renewal
sudo certbot renew --dry-run
```

### Step 4: Test the Setup
Run the test script to verify everything works:

```bash
python3 test_haystack_api.py
```

## API Endpoints

After deployment, the following endpoints will be available:

### OpenAI-Compatible Endpoints
- `POST https://haystack.pmflex.one/haystack/v1/chat/completions`
- `GET https://haystack.pmflex.one/haystack/v1/models`
- `GET https://haystack.pmflex.one/haystack/v1/models/{model_id}`

### Haystack-Specific Endpoints
- `GET https://haystack.pmflex.one/haystack/health`
- `POST https://haystack.pmflex.one/haystack/generate`
- `POST https://haystack.pmflex.one/haystack/rag/initialize`
- `GET https://haystack.pmflex.one/haystack/rag/status`
- `POST https://haystack.pmflex.one/haystack/rag/refresh`
- `POST https://haystack.pmflex.one/haystack/rag/search`

### Project Management Endpoints
- `POST https://haystack.pmflex.one/haystack/generate-project-status-report`
- `POST https://haystack.pmflex.one/haystack/project-management-hints`

## Testing Your Original Command

Your original curl command should now work:

```bash
curl -X POST "https://haystack.pmflex.one/haystack/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistral:latest",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "What is OpenProject"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

## Troubleshooting

### 1. Still Getting 404 Errors
- Verify the FastAPI application is running on port 8000
- Check that the `root_path="/haystack"` is set in `src/main.py`
- Ensure nginx is properly forwarding to `http://localhost:8000/haystack/`

### 2. SSL Certificate Issues
- Verify certificates exist: `sudo ls -la /etc/letsencrypt/live/haystack.pmflex.one/`
- Check certificate expiry: `sudo certbot certificates`
- Renew if needed: `sudo certbot renew`

### 3. Application Not Starting
- Check logs: `docker-compose logs haystack` or application logs
- Verify Ollama is running and accessible
- Check environment variables in `.env` file

### 4. Nginx Configuration Issues
- Test configuration: `sudo nginx -t`
- Check nginx logs: `sudo tail -f /var/log/nginx/error.log`
- Verify nginx is running: `sudo systemctl status nginx`

## Security Considerations

The nginx configuration includes:
- SSL/TLS encryption with modern protocols
- Security headers (HSTS, X-Frame-Options, etc.)
- Rate limiting to prevent abuse
- Proper proxy headers for request forwarding

## Performance Tuning

For production use, consider:
- Adjusting nginx buffer sizes based on response sizes
- Configuring appropriate timeouts for LLM generation
- Setting up monitoring and logging
- Implementing caching for frequently requested data

## Next Steps

1. Deploy the updated application code
2. Configure nginx with the provided example
3. Set up SSL certificates
4. Test all endpoints
5. Monitor logs for any issues
6. Set up monitoring and alerting for production use
