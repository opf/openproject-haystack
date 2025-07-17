#!/usr/bin/env python3
"""Test script for the project management hints endpoint."""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_project_hints():
    """Test the project management hints endpoint."""
    
    # Configuration
    base_url = "http://localhost:8000"
    
    # Example request payload
    request_data = {
        "project": {
            "id": 1,  # Replace with actual project ID
            "type": "project"  # or "portfolio", "program"
        },
        "openproject": {
            "base_url": "https://your-openproject-instance.com",  # Replace with actual URL
            "user_token": "your-api-token-here"  # Replace with actual token
        }
    }
    
    print("Testing Project Management Hints Endpoint")
    print("=" * 50)
    
    try:
        # Make request to the hints endpoint
        response = requests.post(
            f"{base_url}/project-management-hints",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minutes timeout for comprehensive analysis
        )
        
        if response.status_code == 200:
            hints_data = response.json()
            
            print(f"✅ Successfully generated {len(hints_data['hints'])} hints")
            print(f"📊 Performed {hints_data['checks_performed']} automated checks")
            print(f"🏗️ Project ID: {hints_data['project_id']}")
            print(f"🌐 OpenProject URL: {hints_data['openproject_base_url']}")
            print(f"📅 Generated at: {hints_data['generated_at']}")
            
            print("\n📋 HINTS:")
            print("-" * 30)
            
            for i, hint in enumerate(hints_data['hints'], 1):
                print(f"{i}. {hint['title']}")
                print(f"   {hint['description']}")
                print(f"   ☐ Checked: {hint['checked']}")
                print()
            
            if hints_data.get('summary'):
                print("📝 SUMMARY:")
                print("-" * 30)
                print(hints_data['summary'])
            
            # Save response to file for inspection
            with open('project_hints_response.json', 'w', encoding='utf-8') as f:
                json.dump(hints_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Full response saved to: project_hints_response.json")
            
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the server is running on http://localhost:8000")
    except requests.exceptions.Timeout:
        print("❌ Request timeout: The analysis took too long")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_rag_status():
    """Test the RAG system status."""
    base_url = "http://localhost:8000"
    
    print("\nTesting RAG System Status")
    print("=" * 30)
    
    try:
        response = requests.get(f"{base_url}/rag/status")
        
        if response.status_code == 200:
            status_data = response.json()
            print("✅ RAG system status retrieved")
            print(f"📊 Pipeline ready: {status_data.get('validation', {}).get('pipeline_ready', False)}")
            
            pipeline_stats = status_data.get('pipeline_stats', {})
            if 'document_stats' in pipeline_stats:
                doc_stats = pipeline_stats['document_stats']
                print(f"📚 Documents loaded: {doc_stats.get('total_documents', 0)}")
                print(f"🔍 Vector chunks: {doc_stats.get('vector_store_stats', {}).get('total_chunks', 0)}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error checking RAG status: {e}")

if __name__ == "__main__":
    print("🚀 Project Management Hints API Test")
    print("=" * 50)
    
    # First check RAG system status
    test_rag_status()
    
    # Then test the hints endpoint
    print("\n" + "=" * 50)
    test_project_hints()
    
    print("\n" + "=" * 50)
    print("📖 Usage Instructions:")
    print("1. Update the request_data with your actual OpenProject details")
    print("2. Make sure the RAG system is initialized: POST /rag/initialize")
    print("3. Ensure your OpenProject instance is accessible")
    print("4. Run this script to test the endpoint")
    print("\n💡 The endpoint performs 10 automated checks and generates German hints based on PMFlex methodology!")
