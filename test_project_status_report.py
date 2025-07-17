#!/usr/bin/env python3
"""
Test script for the project status report endpoint.
This demonstrates how to use the new endpoint to generate project status reports.
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}


def test_project_status_report():
    """Test the project status report endpoint."""
    print("Testing project status report generation...")
    
    # Example request data
    payload = {
        "project_id": "1",  # Replace with actual project ID
        "openproject_base_url": "https://your-openproject-instance.com"  # Replace with actual URL
    }
    
    # Example API key - replace with actual OpenProject API key
    api_key = "your-openproject-api-key-here"
    headers = {
        **HEADERS,
        "Authorization": f"Bearer {api_key}"
    }
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    print(f"Authorization header: Bearer {api_key[:10]}...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/generate-project-status-report",
            headers=headers,
            json=payload,
            timeout=60  # Longer timeout for report generation
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Project status report generated successfully!")
            print(f"Project ID: {result['project_id']}")
            print(f"Work packages analyzed: {result['work_packages_analyzed']}")
            print(f"Generated at: {result['generated_at']}")
            print(f"OpenProject URL: {result['openproject_base_url']}")
            print("\n" + "="*80)
            print("GENERATED REPORT:")
            print("="*80)
            print(result['report'])
            print("="*80)
        else:
            error_data = response.json()
            print(f"❌ Error: {response.status_code}")
            print(f"Error details: {json.dumps(error_data, indent=2)}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out. Report generation may take longer for large projects.")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server.")
        print("Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def show_usage():
    """Show usage instructions."""
    print("=" * 60)
    print("Project Status Report API Test")
    print("=" * 60)
    print()
    print("Before running this test, you need to:")
    print("1. Have an OpenProject instance running")
    print("2. Get an API key from your OpenProject instance")
    print("3. Know the project ID you want to analyze")
    print("4. Update the configuration in this script:")
    print("   - project_id: Your OpenProject project ID")
    print("   - openproject_base_url: Your OpenProject instance URL")
    print("   - api_key: Your OpenProject API key")
    print()
    print("Example curl command:")
    print('curl -X POST "http://localhost:8000/generate-project-status-report" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -H "Authorization: Bearer YOUR_API_KEY" \\')
    print('  -d \'{')
    print('    "project_id": "1",')
    print('    "openproject_base_url": "https://your-openproject-instance.com"')
    print('  }\'')
    print()


def main():
    """Run the tests."""
    show_usage()
    
    print("Testing server connectivity...")
    if not test_health_check():
        print("❌ Server is not responding. Please start the server first.")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("Running project status report test...")
    print("="*60)
    test_project_status_report()


if __name__ == "__main__":
    main()
