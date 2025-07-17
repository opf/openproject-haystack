#!/usr/bin/env python3
"""Test script for BlockNote AI integration."""

import requests
import json
import sys

def test_blocknote_integration():
    """Test the BlockNote AI integration with the chat completion endpoint."""
    
    # Test data similar to what BlockNote sends
    test_request = {
        "model": "mistral:latest",
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "You're manipulating a text document using HTML blocks. \n        Make sure to follow the json schema provided. When referencing ids they MUST be EXACTLY the same (including the trailing $). \n        List items are 1 block with 1 list item each, so block content `<ul><li>item1</li></ul>` is valid, but `<ul><li>item1</li><li>item2</li></ul>` is invalid. We'll merge them automatically.\n        For code blocks, you can use the `data-language` attribute on a code block to specify the language.\n        This is the document as an array of html blocks (the cursor is BETWEEN two blocks as indicated by cursor: true):"
            },
            {
                "role": "system",
                "content": "[{\"id\":\"e77d39f6-597d-46bb-83c3-2aba55e519f3$\",\"block\":\"<h3 data-level=\\\"3\\\">Planets of the solar system</h3>\"},{\"id\":\"82ec1e48-07ee-4cfa-85e5-da9bf669cbf2$\",\"block\":\"<p></p>\"},{\"cursor\":true}]"
            },
            {
                "role": "system",
                "content": "First, determine what part of the document the user is talking about. You SHOULD probably take cursor info into account if needed.\n       EXAMPLE: if user says \"below\" (without pointing to a specific part of the document) he / she probably indicates the block(s) after the cursor. \n       EXAMPLE: If you want to insert content AT the cursor position (UNLESS indicated otherwise by the user), \n       then you need `referenceId` to point to the block before the cursor with position `after` (or block below and `before`).\n      \n      Prefer updating existing blocks over removing and adding (but this also depends on the user's question)."
            },
            {
                "role": "system",
                "content": "The user asks you to do the following:"
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
                                                "type": {
                                                    "type": "string",
                                                    "enum": ["update"]
                                                },
                                                "id": {
                                                    "type": "string",
                                                    "description": "id of block to update"
                                                },
                                                "block": {
                                                    "$ref": "#/$defs/block"
                                                }
                                            },
                                            "required": ["type", "id", "block"],
                                            "additionalProperties": False
                                        },
                                        {
                                            "type": "object",
                                            "description": "Insert new blocks",
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "enum": ["add"]
                                                },
                                                "referenceId": {
                                                    "type": "string",
                                                    "description": "MUST be an id of a block in the document"
                                                },
                                                "position": {
                                                    "type": "string",
                                                    "enum": ["before", "after"],
                                                    "description": "`after` to add blocks AFTER (below) the block with `referenceId`, `before` to add the block BEFORE (above)"
                                                },
                                                "blocks": {
                                                    "items": {
                                                        "$ref": "#/$defs/block"
                                                    },
                                                    "type": "array"
                                                }
                                            },
                                            "required": ["type", "referenceId", "position", "blocks"],
                                            "additionalProperties": False
                                        },
                                        {
                                            "type": "object",
                                            "description": "Delete a block",
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "enum": ["delete"]
                                                },
                                                "id": {
                                                    "type": "string",
                                                    "description": "id of block to delete"
                                                }
                                            },
                                            "required": ["type", "id"],
                                            "additionalProperties": False
                                        }
                                    ]
                                }
                            }
                        },
                        "additionalProperties": False,
                        "required": ["operations"],
                        "$defs": {
                            "block": {
                                "type": "string",
                                "description": "html of block (MUST be a single HTML element)"
                            }
                        }
                    }
                }
            }
        ],
        "stream": True
    }
    
    # Test endpoint URL (adjust if your server runs on a different port)
    url = "http://localhost:8000/v1/chat/completions"
    
    print("Testing BlockNote AI integration...")
    print(f"Sending request to: {url}")
    
    try:
        response = requests.post(
            url,
            json=test_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("✅ Success! Response received:")
            print(json.dumps(response_data, indent=2))
            
            # Check if it's a tool call response (modern format)
            if (response_data.get("choices") and 
                len(response_data["choices"]) > 0 and
                response_data["choices"][0].get("message", {}).get("tool_calls")):
                
                tool_calls = response_data["choices"][0]["message"]["tool_calls"]
                print(f"\n✅ Tool calls detected: {len(tool_calls)} calls")
                
                for i, tool_call in enumerate(tool_calls):
                    print(f"Tool call {i+1}: {tool_call['function']['name']} (ID: {tool_call['id']})")
                    
                    # Try to parse the function arguments
                    try:
                        args = json.loads(tool_call["function"]["arguments"])
                        print("✅ Function arguments are valid JSON:")
                        print(json.dumps(args, indent=2))
                        
                        # Check if it has the expected structure
                        if "operations" in args and isinstance(args["operations"], list):
                            print(f"✅ Found {len(args['operations'])} operations")
                            for j, op in enumerate(args["operations"]):
                                print(f"  Operation {j+1}: {op.get('type', 'unknown')}")
                        else:
                            print("❌ Missing or invalid 'operations' field")
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ Function arguments are not valid JSON: {e}")
                        print(f"Raw arguments: {tool_call['function']['arguments']}")
                        
            # Check for legacy function_call format
            elif (response_data.get("choices") and 
                  len(response_data["choices"]) > 0 and
                  response_data["choices"][0].get("message", {}).get("function_call")):
                
                function_call = response_data["choices"][0]["message"]["function_call"]
                print(f"\n⚠️ Legacy function call detected: {function_call['name']}")
                print("Note: This is the old format. BlockNote expects tool_calls format.")
                
            else:
                print("❌ Expected tool call response but got regular text response")
                if response_data.get("choices"):
                    content = response_data["choices"][0].get("message", {}).get("content")
                    if content:
                        print(f"Content: {content[:200]}...")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print("Response:", response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure it's running on http://localhost:8000")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    
    return response.status_code == 200

def test_regular_chat():
    """Test that regular chat completion still works."""
    
    regular_request = {
        "model": "mistral:latest",
        "messages": [
            {
                "role": "user",
                "content": "Hello, how are you?"
            }
        ]
    }
    
    url = "http://localhost:8000/v1/chat/completions"
    
    print("\n" + "="*50)
    print("Testing regular chat completion...")
    
    try:
        response = requests.post(
            url,
            json=regular_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            print("✅ Regular chat completion works!")
            
            if (response_data.get("choices") and 
                len(response_data["choices"]) > 0 and
                response_data["choices"][0].get("message", {}).get("content")):
                
                content = response_data["choices"][0]["message"]["content"]
                print(f"Response: {content[:100]}...")
                return True
            else:
                print("❌ No content in response")
                return False
        else:
            print(f"❌ Regular chat failed with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Regular chat test failed: {e}")
        return False

if __name__ == "__main__":
    print("BlockNote AI Integration Test")
    print("="*50)
    
    # Test BlockNote integration
    blocknote_success = test_blocknote_integration()
    
    # Test regular chat still works
    regular_success = test_regular_chat()
    
    print("\n" + "="*50)
    print("Test Results:")
    print(f"BlockNote Integration: {'✅ PASS' if blocknote_success else '❌ FAIL'}")
    print(f"Regular Chat: {'✅ PASS' if regular_success else '❌ FAIL'}")
    
    if blocknote_success and regular_success:
        print("\n🎉 All tests passed! BlockNote AI integration is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        sys.exit(1)
