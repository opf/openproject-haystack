"""OpenProject API client for fetching work packages and project data."""

import httpx
import logging
import base64
from typing import List, Dict, Any, Optional
from src.models.schemas import WorkPackage

logger = logging.getLogger(__name__)


class OpenProjectAPIError(Exception):
    """Custom exception for OpenProject API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class OpenProjectClient:
    """Client for interacting with OpenProject API."""
    
    def __init__(self, base_url: str, api_key: str):
        """Initialize the OpenProject client.
        
        Args:
            base_url: Base URL of the OpenProject instance
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        # Create Basic auth header using base64 encoding of 'apikey:' + api_key
        auth_string = f"apikey:{api_key}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_auth}",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/hal+json",
            "Content-Type": "application/json"
        }
    
    async def get_work_packages(self, project_id: str) -> List[WorkPackage]:
        """Fetch all work packages for a specific project.
        
        Args:
            project_id: The OpenProject project ID
            
        Returns:
            List of WorkPackage objects
            
        Raises:
            OpenProjectAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v3/projects/{project_id}/work_packages"
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.info(f"Fetching work packages from: {url}")
                
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 401:
                    raise OpenProjectAPIError(
                        "Invalid API key or insufficient permissions", 
                        status_code=401
                    )
                elif response.status_code == 403:
                    raise OpenProjectAPIError(
                        "Insufficient permissions to access this project", 
                        status_code=403
                    )
                elif response.status_code == 404:
                    raise OpenProjectAPIError(
                        f"Project with ID '{project_id}' not found", 
                        status_code=404
                    )
                elif response.status_code != 200:
                    raise OpenProjectAPIError(
                        f"OpenProject API returned status {response.status_code}: {response.text}",
                        status_code=response.status_code
                    )
                
                data = response.json()
                work_packages = []
                
                # Parse work packages from the response
                if "_embedded" in data and "elements" in data["_embedded"]:
                    for wp_data in data["_embedded"]["elements"]:
                        try:
                            work_package = self._parse_work_package(wp_data)
                            work_packages.append(work_package)
                        except Exception as e:
                            logger.warning(f"Failed to parse work package {wp_data.get('id', 'unknown')}: {e}")
                            continue
                
                logger.info(f"Successfully fetched {len(work_packages)} work packages")
                return work_packages
                
        except httpx.TimeoutException:
            raise OpenProjectAPIError("Request to OpenProject API timed out", status_code=408)
        except httpx.ConnectError:
            raise OpenProjectAPIError("Could not connect to OpenProject API", status_code=503)
        except httpx.HTTPError as e:
            raise OpenProjectAPIError(f"HTTP error occurred: {str(e)}", status_code=500)
        except Exception as e:
            if isinstance(e, OpenProjectAPIError):
                raise
            raise OpenProjectAPIError(f"Unexpected error: {str(e)}", status_code=500)
    
    def _parse_work_package(self, wp_data: Dict[str, Any]) -> WorkPackage:
        """Parse work package data from OpenProject API response.
        
        Args:
            wp_data: Raw work package data from API
            
        Returns:
            WorkPackage object
        """
        # Extract status information
        status = {}
        if "status" in wp_data and wp_data["status"]:
            status = {
                "id": wp_data["status"].get("id"),
                "name": wp_data["status"].get("name"),
                "href": wp_data["status"].get("href")
            }
        
        # Extract priority information
        priority = None
        if "priority" in wp_data and wp_data["priority"]:
            priority = {
                "id": wp_data["priority"].get("id"),
                "name": wp_data["priority"].get("name"),
                "href": wp_data["priority"].get("href")
            }
        
        # Extract assignee information
        assignee = None
        if "assignee" in wp_data and wp_data["assignee"]:
            assignee = {
                "id": wp_data["assignee"].get("id"),
                "name": wp_data["assignee"].get("name"),
                "href": wp_data["assignee"].get("href")
            }
        
        # Extract description
        description = None
        if "description" in wp_data and wp_data["description"]:
            description = {
                "format": wp_data["description"].get("format"),
                "raw": wp_data["description"].get("raw"),
                "html": wp_data["description"].get("html")
            }
        
        return WorkPackage(
            id=wp_data["id"],
            subject=wp_data.get("subject", ""),
            status=status,
            priority=priority,
            assignee=assignee,
            due_date=wp_data.get("dueDate"),
            done_ratio=wp_data.get("percentageDone"),
            created_at=wp_data.get("createdAt", ""),
            updated_at=wp_data.get("updatedAt", ""),
            description=description
        )
    
    async def get_project_info(self, project_id: str) -> Dict[str, Any]:
        """Fetch basic project information.
        
        Args:
            project_id: The OpenProject project ID
            
        Returns:
            Project information dictionary
            
        Raises:
            OpenProjectAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v3/projects/{project_id}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Fetching project info from: {url}")
                
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 401:
                    raise OpenProjectAPIError(
                        "Invalid API key or insufficient permissions", 
                        status_code=401
                    )
                elif response.status_code == 403:
                    raise OpenProjectAPIError(
                        "Insufficient permissions to access this project", 
                        status_code=403
                    )
                elif response.status_code == 404:
                    raise OpenProjectAPIError(
                        f"Project with ID '{project_id}' not found", 
                        status_code=404
                    )
                elif response.status_code != 200:
                    raise OpenProjectAPIError(
                        f"OpenProject API returned status {response.status_code}: {response.text}",
                        status_code=response.status_code
                    )
                
                return response.json()
                
        except httpx.TimeoutException:
            raise OpenProjectAPIError("Request to OpenProject API timed out", status_code=408)
        except httpx.ConnectError:
            raise OpenProjectAPIError("Could not connect to OpenProject API", status_code=503)
        except httpx.HTTPError as e:
            raise OpenProjectAPIError(f"HTTP error occurred: {str(e)}", status_code=500)
        except Exception as e:
            if isinstance(e, OpenProjectAPIError):
                raise
            raise OpenProjectAPIError(f"Unexpected error: {str(e)}", status_code=500)
