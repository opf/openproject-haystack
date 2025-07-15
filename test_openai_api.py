#!/usr/bin/env python3
"""
Test script for the OpenAI-compatible API endpoints.
This demonstrates how to use the API with both direct requests and OpenAI client library.
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}


def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()


def test_list_models():
    """Test the models listing endpoint."""
    print("Testing models listing...")
    response = requests.get(f"{BASE_URL}/v1/models")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_chat_completion():
    """Test the chat completion endpoint."""
    print("Testing chat completion...")
    
    payload = {
        "model": "mistral:latest",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Can you tell me a short joke?"}
        ],
        "temperature": 0.7,
        "max_tokens": 150
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers=HEADERS,
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        print(f"Assistant's message: {result['choices'][0]['message']['content']}")
    else:
        print(f"Error: {response.text}")
    print()


def test_conversation():
    """Test a multi-turn conversation."""
    print("Testing multi-turn conversation...")
    
    payload = {
        "model": "mistral:latest",
        "messages": [
            {"role": "system", "content": "You are a helpful programming assistant."},
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a high-level, interpreted programming language known for its simplicity and readability."},
            {"role": "user", "content": "Can you give me a simple Python example?"}
        ],
        "temperature": 0.5,
        "max_tokens": 200
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers=HEADERS,
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Assistant's response: {result['choices'][0]['message']['content']}")
        print(f"Token usage: {result['usage']}")
    else:
        print(f"Error: {response.text}")
    print()


def test_with_openai_client():
    """Test using the OpenAI Python client library."""
    try:
        from openai import OpenAI
        
        print("Testing with OpenAI client library...")
        
        # Create client pointing to local server
        client = OpenAI(
            base_url=f"{BASE_URL}/v1",
            api_key="dummy-key"  # Not used but required by client
        )
        
        # Test chat completion
        response = client.chat.completions.create(
            model="mistral:latest",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Explain what an API is in simple terms."}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        print(f"Response: {response.choices[0].message.content}")
        print(f"Usage: {response.usage}")
        print()
        
    except ImportError:
        print("OpenAI client library not installed. Install with: pip install openai")
        print("Skipping OpenAI client test...")
        print()


def main():
    """Run all tests."""
    print("=" * 50)
    print("OpenProject Haystack - OpenAI API Compatibility Test")
    print("=" * 50)
    print()
    
    try:
        test_health_check()
        test_list_models()
        test_chat_completion()
        test_conversation()
        test_with_openai_client()
        
        print("All tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server.")
        print("Make sure the server is running on http://localhost:8000")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
