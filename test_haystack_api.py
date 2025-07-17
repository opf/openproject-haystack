#!/usr/bin/env python3
"""Test script to verify Haystack API endpoints work with /haystack prefix."""

import requests
import json
import sys

def test_health_endpoint():
    """Test the health endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get("https://haystack.pmflex.one/haystack/health")
        print(f"Health endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"Error testing health endpoint: {e}")
        return False

def test_chat_completions():
    """Test the OpenAI-compatible chat completions endpoint."""
    print("\nTesting chat completions endpoint...")
    
    payload = {
        "model": "mistral:latest",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is OpenProject?"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            "https://haystack.pmflex.one/haystack/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        print(f"Chat completions status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Success! Response structure:")
            print(f"- ID: {result.get('id')}")
            print(f"- Model: {result.get('model')}")
            print(f"- Choices: {len(result.get('choices', []))}")
            if result.get('choices'):
                print(f"- Message: {result['choices'][0]['message']['content'][:100]}...")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error testing chat completions: {e}")
        return False

def test_models_endpoint():
    """Test the models listing endpoint."""
    print("\nTesting models endpoint...")
    try:
        response = requests.get("https://haystack.pmflex.one/haystack/v1/models")
        print(f"Models endpoint status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Available models: {len(result.get('data', []))}")
            for model in result.get('data', []):
                print(f"- {model.get('id')}")
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"Error testing models endpoint: {e}")
        return False

def main():
    """Run all API tests."""
    print("Testing Haystack API with /haystack prefix...")
    print("=" * 50)
    
    tests = [
        test_health_endpoint,
        test_models_endpoint,
        test_chat_completions
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    print("Test Results:")
    test_names = ["Health", "Models", "Chat Completions"]
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name}: {status}")
    
    if all(results):
        print("\n🎉 All tests passed! The /haystack prefix is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Check the nginx configuration and application deployment.")
        sys.exit(1)

if __name__ == "__main__":
    main()
