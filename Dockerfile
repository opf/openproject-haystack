FROM python:3.11-slim

# System dependencies for ollama-haystack
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Entrypoint for development
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
