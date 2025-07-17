# BlockNote AI Integration

This document describes the BlockNote AI integration implemented in the OpenProject Haystack system.

## Overview

BlockNote AI is a rich text editor that uses AI to help users manipulate document content. This integration allows BlockNote to use your local Ollama models through an OpenAI-compatible API endpoint with function calling support.

## Problem Solved

Previously, when BlockNote AI sent requests to the chat completion endpoint, it would receive responses with explanatory text instead of the clean JSON operations it expected:

**Before (Problematic Response):**
```json
{
  "choices": [{
    "message": {
      "role": "assistant", 
      "content": "To respond to the user's request, we need to update the second block in the document. Here's how the updated document would look like:\n\n```json\n[{\"id\":\"9d713335-137f-40a3-9afd-c38ef85cf5fd$\",\"block\":\"<h3 data-level=\\\"3\\\">Planets of the solar system</h3>\"},\n {\"id\":\"2dd367c3-cb3e-4dc0-93da-3fe5a3934b1c$\",\"block\":\"<ul><li>Mercury</li><li>Venus</li><li>Earth</li><li>Mars</li><li>Jupiter</li><li>Saturn</li><li>Uranus</li><li>Neptune</li></ul>\"}]\n```\n\nIn this updated document, the second block now contains an unordered list of all planets in our solar system."
    }
  }]
}
```

**After (Correct Function Call Response):**
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "function_call": {
        "name": "json",
        "arguments": "{\"operations\":[{\"type\":\"update\",\"id\":\"82ec1e48-07ee-4cfa-85e5-da9bf669cbf2$\",\"block\":\"<ul><li>Mercury</li></ul>\"},{\"type\":\"add\",\"referenceId\":\"82ec1e48-07ee-4cfa-85e5-da9bf669cbf2$\",\"position\":\"after\",\"blocks\":[\"<ul><li>Venus</li></ul>\",\"<ul><li>Earth</li></ul>\",\"<ul><li>Mars</li></ul>\",\"<ul><li>Jupiter</li></ul>\",\"<ul><li>Saturn</li></ul>\",\"<ul><li>Uranus</li></ul>\",\"<ul><li>Neptune</li></ul>\"]}]}"
      }
    },
    "finish_reason": "function_call"
  }]
}
```

## Implementation Details

### 1. Enhanced Data Models (`src/models/schemas.py`)

Added support for OpenAI function calling:

- `FunctionCall`: Represents a function call with name and arguments
- `ToolFunction`: Defines a function that can be called
- `Tool`: Wraps a function definition
- `ToolChoice`: Specifies which function to call
- Enhanced `ChatMessage` to support function calls
- Enhanced `ChatCompletionRequest` to accept tools and tool_choice
- Enhanced `ChatChoice` to support "function_call" finish reason

### 2. Generation Pipeline (`src/pipelines/generation.py`)

Added BlockNote-specific processing:

- `_is_blocknote_request()`: Detects BlockNote function calling requests
- `_handle_blocknote_function_call()`: Processes BlockNote requests with enhanced prompting
- `_create_blocknote_prompt()`: Creates prompts optimized for JSON schema compliance
- `_process_blocknote_response()`: Validates and cleans AI responses to ensure valid JSON

### 3. API Endpoint (`src/api/routes.py`)

Enhanced the `/v1/chat/completions` endpoint:

- Detects function calling requests
- Routes BlockNote requests through specialized processing
- Returns properly formatted function call responses
- Maintains backward compatibility with regular chat requests

## Key Features

### 1. Automatic Detection
The system automatically detects BlockNote requests by checking for:
- `tools` parameter with a "json" function
- `tool_choice` parameter specifying the "json" function

### 2. Enhanced Prompting
BlockNote requests get special prompt engineering:
- Clear instructions to return only JSON
- Schema validation requirements
- BlockNote-specific rules (e.g., one list item per block)

### 3. Response Validation
All BlockNote responses are validated to ensure:
- Valid JSON structure
- Required fields present
- Correct operation types
- Proper block ID preservation

### 4. Error Handling
Robust error handling with fallback responses:
- JSON parsing errors return helpful error blocks
- Validation failures provide specific error messages
- Malformed responses are gracefully handled

### 5. Backward Compatibility
Regular chat completion requests continue to work unchanged.

## BlockNote Request Format

BlockNote sends requests with this structure:

```json
{
  "model": "mistral:latest",
  "temperature": 0,
  "messages": [
    {
      "role": "system",
      "content": "You're manipulating a text document using HTML blocks..."
    },
    {
      "role": "system", 
      "content": "[{\"id\":\"block-id$\",\"block\":\"<p>content</p>\"}]"
    },
    {
      "role": "user",
      "content": "List the planets of the solar system"
    }
  ],
  "tool_choice": {
    "type": "function",
    "function": {"name": "json"}
  },
  "tools": [{
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
                    "type": {"enum": ["update"]},
                    "id": {"type": "string"},
                    "block": {"type": "string"}
                  }
                },
                {
                  "type": "object", 
                  "description": "Insert new blocks",
                  "properties": {
                    "type": {"enum": ["add"]},
                    "referenceId": {"type": "string"},
                    "position": {"enum": ["before", "after"]},
                    "blocks": {"type": "array", "items": {"type": "string"}}
                  }
                },
                {
                  "type": "object",
                  "description": "Delete a block", 
                  "properties": {
                    "type": {"enum": ["delete"]},
                    "id": {"type": "string"}
                  }
                }
              ]
            }
          }
        }
      }
    }
  }],
  "stream": true
}
```

## Expected Response Format

The system returns OpenAI-compatible function call responses:

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1752741183,
  "model": "mistral:latest",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": null,
      "function_call": {
        "name": "json",
        "arguments": "{\"operations\":[{\"type\":\"update\",\"id\":\"82ec1e48-07ee-4cfa-85e5-da9bf669cbf2$\",\"block\":\"<ul><li>Mercury</li></ul>\"}]}"
      }
    },
    "finish_reason": "function_call"
  }],
  "usage": {
    "prompt_tokens": 394,
    "completion_tokens": 140,
    "total_tokens": 534
  }
}
```

## Testing

Use the provided test script to verify the integration:

```bash
python test_blocknote_integration.py
```

This script tests:
1. BlockNote function calling requests
2. Regular chat completion requests (backward compatibility)
3. Response format validation
4. JSON parsing and structure validation

## Configuration

No additional configuration is required. The integration works with your existing:
- Ollama models
- API settings
- Authentication setup

## Troubleshooting

### Common Issues

1. **AI returns explanatory text instead of JSON**
   - The enhanced prompting should prevent this
   - Check logs for validation errors
   - Verify the AI model supports JSON format requests

2. **Invalid JSON responses**
   - The system includes fallback error handling
   - Check the `_process_blocknote_response()` logs
   - Verify the AI model is properly configured

3. **Missing function call in response**
   - Ensure the request includes both `tools` and `tool_choice`
   - Check that the "json" function is properly defined
   - Verify the request detection logic

### Debugging

Enable debug logging to see detailed processing:

```python
import logging
logging.getLogger("src.pipelines.generation").setLevel(logging.DEBUG)
```

## Performance Considerations

- BlockNote requests use lower temperature (0.1) for more consistent JSON
- Response validation adds minimal overhead
- Fallback error handling prevents system crashes
- Regular chat requests are unaffected

## Future Enhancements

Potential improvements:
1. Support for streaming responses
2. More sophisticated JSON schema validation
3. Custom BlockNote operation types
4. Performance optimizations for large documents
5. Enhanced error messages for specific validation failures
