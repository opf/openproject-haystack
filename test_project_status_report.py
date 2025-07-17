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
    
    # Example request data - updated to match current API structure
    payload = {
        "project": {
            "id": 8,  # Replace with actual project ID
            "type": "project"  # or "portfolio", "program"
        },
        "openproject": {
            "base_url": "https://pmflex.one/",  # Replace with actual URL
            "user_token": "881dc9aef285ee58c1265ccb5de5272e54608bc7a9acbfe575294b35c72607c8"  # Replace with actual token
        },
        "debug": "true"
    }
    
    headers = HEADERS
    
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    print(f"User token: {payload['openproject']['user_token'][:10]}...")
    
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
    print("   - project.id: Your OpenProject project ID")
    print("   - project.type: Type of project (project, portfolio, program)")
    print("   - openproject.base_url: Your OpenProject instance URL")
    print("   - openproject.user_token: Your OpenProject API key")
    print()
    print("Example curl command:")
    print('curl -X POST "http://localhost:8000/generate-project-status-report" \\')
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{')
    print('    "project": {')
    print('      "id": 1,')
    print('      "type": "project"')
    print('    },')
    print('    "openproject": {')
    print('      "base_url": "https://your-openproject-instance.com",')
    print('      "user_token": "your-api-token-here"')
    print('    }')
    print('  }\'')
    print()
    print("📝 Note: Reports are now generated in German following PMFlex methodology!")
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
