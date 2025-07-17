#!/usr/bin/env python3
"""Test script for BlockNote AI streaming integration."""

import requests
import json
import sys

def test_blocknote_streaming():
    """Test the BlockNote AI streaming integration."""
    
    # Test data similar to what BlockNote sends with streaming enabled
    test_request = {
        "model": "mistral:latest",
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You're manipulating a text document using HTML blocks. Make sure to follow the json schema provided. When referencing ids they MUST be EXACTLY the same (including the trailing $)."
            },
            {
                "role": "system",
                "content": "[{\"id\":\"e77d39f6-597d-46bb-83c3-2aba55e519f3$\",\"block\":\"<h3 data-level=\\\"3\\\">Planets of the solar system</h3>\"},{\"id\":\"82ec1e48-07ee-4cfa-85e5-da9bf669cbf2$\",\"block\":\"<p></p>\"},{\"cursor\":true}]"
            },
            {
                "role": "user",
                "content": "List the planets of the solar system"
            }
        ],
        "tool_choice": {
            "type": "function",
            "function": {
                "name": "json"
            }
        },
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "json",
                    "description": "Respond with a JSON object.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "operations": {
                                "type": "array",
                                "items": {
                                    "anyOf": [
                                        {
                                            "type": "object",
                                            "description": "Update a block",
                                            "properties": {
                                                "type": {"type": "string", "enum": ["update"]},
                                                "id": {"type": "string"},
                                                "block": {"type": "string"}
                                            },
                                            "required": ["type", "id", "block"]
                                        }
                                    ]
                                }
                            }
                        },
                        "required": ["operations"]
                    }
                }
            }
        ],
        "stream": True
    }
    
    url = "https://haystack.pmflex.one/haystack/v1/chat/completions"
    
    print("Testing BlockNote AI streaming integration...")
    print(f"Sending streaming request to: {url}")
    
    try:
        response = requests.post(
            url,
            json=test_request,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Streaming response received!")
            
            # Parse streaming response
            chunks = []
            tool_call_id = None
            arguments_buffer = ""
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]  # Remove 'data: ' prefix
                        
                        if data_str == '[DONE]':
                            print("✅ Stream completed with [DONE]")
                            break
                        
                        try:
                            chunk_data = json.loads(data_str)
                            chunks.append(chunk_data)
                            
                            # Check for tool calls in delta
                            if (chunk_data.get("choices") and 
                                len(chunk_data["choices"]) > 0 and
                                chunk_data["choices"][0].get("delta", {}).get("tool_calls")):
                                
                                tool_calls = chunk_data["choices"][0]["delta"]["tool_calls"]
                                for tool_call in tool_calls:
                                    if tool_call.get("id"):
                                        tool_call_id = tool_call["id"]
                                        print(f"✅ Tool call started: {tool_call_id}")
                                    
                                    if tool_call.get("function", {}).get("arguments"):
                                        arguments_buffer += tool_call["function"]["arguments"]
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Failed to parse chunk: {e}")
                            print(f"Raw chunk: {data_str}")
            
            print(f"\n✅ Received {len(chunks)} chunks")
            
            if tool_call_id:
                print(f"✅ Tool call ID: {tool_call_id}")
                
                # Try to parse the accumulated arguments
                if arguments_buffer:
                    try:
                        args = json.loads(arguments_buffer)
                        print("✅ Streamed arguments are valid JSON:")
                        print(json.dumps(args, indent=2))
                        
                        # Check if it has the expected structure
                        if "operations" in args and isinstance(args["operations"], list):
                            print(f"✅ Found {len(args['operations'])} operations")
                            for i, op in enumerate(args["operations"]):
                                print(f"  Operation {i+1}: {op.get('type', 'unknown')}")
                        else:
                            print("❌ Missing or invalid 'operations' field")
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ Streamed arguments are not valid JSON: {e}")
                        print(f"Raw arguments: {arguments_buffer}")
                else:
                    print("❌ No arguments received in stream")
            else:
                print("❌ No tool call ID found in stream")
            
            return True
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print("Response:", response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure it's running on http://localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_regular_streaming():
    """Test regular streaming (non-tool call)."""
    
    regular_request = {
        "model": "mistral:latest",
        "messages": [
            {
                "role": "user",
                "content": "Write a short poem about AI"
            }
        ],
        "stream": True
    }
    
    url = "https://haystack.pmflex.one/haystack/v1/chat/completions"
    
    print("\n" + "="*50)
    print("Testing regular streaming...")
    
    try:
        response = requests.post(
            url,
            json=regular_request,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Regular streaming works!")
            
            content_buffer = ""
            chunk_count = 0
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data_str = line_str[6:]
                        
                        if data_str == '[DONE]':
                            print("✅ Stream completed")
                            break
                        
                        try:
                            chunk_data = json.loads(data_str)
                            chunk_count += 1
                            
                            if (chunk_data.get("choices") and 
                                len(chunk_data["choices"]) > 0 and
                                chunk_data["choices"][0].get("delta", {}).get("content")):
                                
                                content = chunk_data["choices"][0]["delta"]["content"]
                                content_buffer += content
                                
                        except json.JSONDecodeError:
                            pass  # Skip invalid chunks
            
            print(f"✅ Received {chunk_count} chunks")
            if content_buffer:
                print(f"Content preview: {content_buffer[:100]}...")
                return True
            else:
                print("❌ No content received")
                return False
        else:
            print(f"❌ Regular streaming failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Regular streaming test failed: {e}")
        return False

if __name__ == "__main__":
    print("BlockNote AI Streaming Integration Test")
    print("="*50)
    
    # Test BlockNote streaming
    blocknote_success = test_blocknote_streaming()
    
    # Test regular streaming
    regular_success = test_regular_streaming()
    
    print("\n" + "="*50)
    print("Test Results:")
    print(f"BlockNote Streaming: {'✅ PASS' if blocknote_success else '❌ FAIL'}")
    print(f"Regular Streaming: {'✅ PASS' if regular_success else '❌ FAIL'}")
    
    if blocknote_success and regular_success:
        print("\n🎉 All streaming tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some streaming tests failed.")
        sys.exit(1)
