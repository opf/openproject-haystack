"""OpenProject API client for fetching work packages and project data."""

import httpx
import logging
import base64
from typing import List, Dict, Any, Optional
from src.models.schemas import WorkPackage

logger = logging.getLogger(__name__)


def normalize_status_name(status_name: str) -> str:
    """Normalize status names to handle common variations.
    
    Args:
        status_name: Raw status name from OpenProject
        
    Returns:
        Normalized status name
    """
    if not status_name or not status_name.strip():
        return "Unknown Status"
    
    # Clean up the status name
    normalized = status_name.strip()
    
    # Handle common status name variations and translations
    status_mappings = {
        # German to English mappings
        "im plan": "In Plan",
        "in planung": "In Plan", 
        "geplant": "In Plan",
        "neu": "New",
        "offen": "Open",
        "in bearbeitung": "In Progress",
        "bearbeitung": "In Progress",
        "in arbeit": "In Progress",
        "erledigt": "Done",
        "abgeschlossen": "Done",
        "geschlossen": "Closed",
        "zurückgestellt": "On Hold",
        "pausiert": "On Hold",
        "abgebrochen": "Cancelled",
        "storniert": "Cancelled",
        
        # English variations
        "in progress": "In Progress",
        "in work": "In Progress",
        "working": "In Progress",
        "completed": "Done",
        "finished": "Done",
        "resolved": "Done",
        "closed": "Closed",
        "on hold": "On Hold",
        "paused": "On Hold",
        "cancelled": "Cancelled",
        "canceled": "Cancelled",
        
        # Common variations
        "todo": "To Do",
        "to-do": "To Do",
        "doing": "In Progress",
        "review": "In Review",
        "testing": "Testing",
        "approved": "Approved",
        "rejected": "Rejected"
    }
    
    # Check for exact matches (case insensitive)
    normalized_lower = normalized.lower()
    if normalized_lower in status_mappings:
        return status_mappings[normalized_lower]
    
    # Check for partial matches
    for key, value in status_mappings.items():
        if key in normalized_lower:
            return value
    
    # Return original if no mapping found, but capitalize properly
    return normalized.title()


class OpenProjectAPIError(Exception):
    """Custom exception for OpenProject API errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class OpenProjectClient:
    """Client for interacting with OpenProject API."""
    
    def __init__(self, base_url: str, api_key: str, debug: bool = False):
        """Initialize the OpenProject client.
        
        Args:
            base_url: Base URL of the OpenProject instance
            api_key: API key for authentication
            debug: If True, use Basic auth with apikey prefix. If False, use Bearer token.
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.debug = debug
        
        # Set authorization header based on debug mode
        if debug:
            # Debug mode: Use Basic auth with apikey prefix (current behavior)
            auth_string = f"apikey:{api_key}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            authorization_header = f"Basic {encoded_auth}"
        else:
            # Production mode: Use Bearer token
            authorization_header = f"Bearer {api_key}"
        
        self.headers = {
            "Authorization": authorization_header,
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/hal+json",
            "Content-Type": "application/json"
        }
    
    async def get_work_packages(self, project_id: str) -> List[WorkPackage]:
        """Fetch all work packages for a specific project using the working query format.
        
        Args:
            project_id: The OpenProject project ID
            
        Returns:
            List of WorkPackage objects
            
        Raises:
            OpenProjectAPIError: If API request fails
        """
        logger.info(f"🚀 STARTING WORK PACKAGE FETCH FOR PROJECT {project_id}")
        
        # First try the working query format that includes all required fields
        try:
            logger.info("🔄 Attempting query_props method first...")
            result = await self._get_work_packages_with_query_props(project_id)
            logger.info(f"✅ Query_props method succeeded, returning {len(result)} work packages")
            return result
        except Exception as e:
            logger.error(f"❌ Query props method failed with error: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            logger.info("🔄 Falling back to API v3 method...")
            try:
                result = await self._get_work_packages_api_v3(project_id)
                logger.info(f"✅ API v3 fallback succeeded, returning {len(result)} work packages")
                return result
            except Exception as fallback_error:
                logger.error(f"❌ API v3 fallback also failed: {fallback_error}")
                raise fallback_error
    
    async def _get_work_packages_with_query_props(self, project_id: str) -> List[WorkPackage]:
        """Fetch work packages using the working query_props format.
        
        Args:
            project_id: The OpenProject project ID
            
        Returns:
            List of WorkPackage objects
        """
        # Use the working query format that includes all required fields
        import json
        query_props = {
            "c": ["id", "type", "subject", "status", "assignee", "priority", "dueDate", "percentageDone"],
            "hi": True,
            "g": "",
            "is": True,
            "tv": False,
            "hla": ["status", "priority", "dueDate"],
            "t": "id:asc",
            "f": [
                {
                    "project": {
                        "operator": "=",
                        "values": [project_id]
                    }
                }
            ],  # Add project filter to ensure we only get work packages from this project
            "ts": "PT0S",
            "pp": 100,  # Fetch up to 100 work packages
            "pa": 1
        }
        
        # Get project info to determine the project identifier/slug
        project_info = await self.get_project_info(project_id)
        project_identifier = project_info.get("identifier", project_id)
        
        url = f"{self.base_url}/projects/{project_identifier}/work_packages"
        params = {
            "query_props": json.dumps(query_props)
        }
        
        logger.info(f"🔍 FETCHING WORK PACKAGES WITH QUERY PROPS")
        logger.info(f"URL: {url}")
        logger.info(f"Query props: {query_props}")
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.info(f"Fetching work packages from: {url} with params: {params}")
                
                response = await client.get(url, headers=self.headers, params=params)
                
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
                
                logger.info(f"📋 QUERY PROPS RESPONSE STRUCTURE:")
                logger.info(f"Response keys: {list(data.keys())}")
                logger.debug(f"Complete response: {data}")
                
                # Parse work packages from the response - query_props format might be different
                elements = []
                if "_embedded" in data and "elements" in data["_embedded"]:
                    # Standard HAL+JSON format
                    elements = data["_embedded"]["elements"]
                    logger.info(f"Found {len(elements)} work packages in _embedded.elements")
                elif "work_packages" in data:
                    # Possible query_props format
                    elements = data["work_packages"]
                    logger.info(f"Found {len(elements)} work packages in work_packages field")
                elif isinstance(data, list):
                    # Direct array format
                    elements = data
                    logger.info(f"Found {len(elements)} work packages in direct array")
                else:
                    logger.warning(f"Unknown response format, trying to find work packages in: {list(data.keys())}")
                    # Try to find work packages in any array field
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 0:
                            # Check if this looks like work packages
                            first_item = value[0]
                            if isinstance(first_item, dict) and ("id" in first_item or "subject" in first_item):
                                elements = value
                                logger.info(f"Found {len(elements)} work packages in '{key}' field")
                                break
                
                if not elements:
                    logger.warning("No work packages found in response")
                    return []
                
                # Parse each work package
                for wp_data in elements:
                    try:
                        work_package = self._parse_work_package_query_props(wp_data)
                        work_packages.append(work_package)
                    except Exception as e:
                        logger.warning(f"Failed to parse work package {wp_data.get('id', 'unknown')}: {e}")
                        continue
                
                logger.info(f"✅ Successfully fetched {len(work_packages)} work packages with query_props")
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
    
    async def _get_work_packages_api_v3(self, project_id: str) -> List[WorkPackage]:
        """Fallback method using API v3 endpoint.
        
        Args:
            project_id: The OpenProject project ID
            
        Returns:
            List of WorkPackage objects
        """
        url = f"{self.base_url}/api/v3/projects/{project_id}/work_packages"
        params = {
            "pageSize": 100,
            "offset": 1,
            "embed": "status,priority,assignee,type,project"
        }
        
        logger.info(f"🔄 FALLBACK: Using API v3 method")
        logger.info(f"URL: {url}")
        logger.info(f"Params: {params}")
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(url, headers=self.headers, params=params)
                
                if response.status_code == 401:
                    raise OpenProjectAPIError("Invalid API key or insufficient permissions", status_code=401)
                elif response.status_code == 403:
                    raise OpenProjectAPIError("Insufficient permissions to access this project", status_code=403)
                elif response.status_code == 404:
                    raise OpenProjectAPIError(f"Project with ID '{project_id}' not found", status_code=404)
                elif response.status_code != 200:
                    raise OpenProjectAPIError(f"OpenProject API returned status {response.status_code}: {response.text}", status_code=response.status_code)
                
                data = response.json()
                work_packages = []
                
                if "_embedded" in data and "elements" in data["_embedded"]:
                    for wp_data in data["_embedded"]["elements"]:
                        try:
                            work_package = self._parse_work_package(wp_data)
                            work_packages.append(work_package)
                        except Exception as e:
                            logger.warning(f"Failed to parse work package {wp_data.get('id', 'unknown')}: {e}")
                            continue
                
                logger.info(f"Successfully fetched {len(work_packages)} work packages via API v3 fallback")
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
    
    async def get_recent_activities(self, project_id: str, days: int = 7, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch recent activities for a project efficiently.
        
        Args:
            project_id: The OpenProject project ID
            days: Number of days to look back for activities (default: 7)
            limit: Maximum number of activities to return (default: 5)
            
        Returns:
            List of recent activity dictionaries
            
        Raises:
            OpenProjectAPIError: If API request fails
        """
        from datetime import datetime, timedelta
        
        # Calculate the date filter for the last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        url = f"{self.base_url}/api/v3/activities"
        params = {
            "filters": f'[{{"project":{{"operator":"=","values":["{project_id}"]}},"createdAt":{{"operator":">=","values":["{cutoff_iso}"]}}}}]',
            "sortBy": '[["createdAt","desc"]]',
            "pageSize": limit
        }
        
        logger.info(f"🔍 FETCHING RECENT ACTIVITIES")
        logger.info(f"Project ID: {project_id}")
        logger.info(f"Time window: Last {days} days (since {cutoff_iso})")
        logger.info(f"Limit: {limit} activities")
        logger.info(f"URL: {url}")
        logger.info(f"Filters: {params['filters']}")
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(url, headers=self.headers, params=params)
                
                if response.status_code == 401:
                    raise OpenProjectAPIError("Invalid API key or insufficient permissions", status_code=401)
                elif response.status_code == 403:
                    raise OpenProjectAPIError("Insufficient permissions to access activities", status_code=403)
                elif response.status_code == 404:
                    logger.info("No activities found for this project")
                    return []
                elif response.status_code != 200:
                    logger.warning(f"Activities API returned status {response.status_code}: {response.text}")
                    return []
                
                data = response.json()
                activities = []
                
                if "_embedded" in data and "elements" in data["_embedded"]:
                    activities = data["_embedded"]["elements"]
                
                logger.info(f"✅ Successfully fetched {len(activities)} recent activities")
                
                # Log activity details for debugging
                for i, activity in enumerate(activities, 1):
                    activity_type = activity.get("_type", "Unknown")
                    created_at = activity.get("createdAt", "Unknown")
                    user_name = "Unknown"
                    if "user" in activity and activity["user"]:
                        user_name = activity["user"].get("name", "Unknown")
                    
                    work_package_info = "No WP"
                    if "workPackage" in activity and activity["workPackage"]:
                        wp_id = activity["workPackage"].get("id", "Unknown")
                        wp_subject = activity["workPackage"].get("subject", "Unknown")
                        work_package_info = f"WP {wp_id}: {wp_subject}"
                    
                    logger.info(f"  {i}. [{activity_type}] {user_name} @ {created_at}")
                    logger.info(f"     Related to: {work_package_info}")
                
                return activities
                
        except httpx.TimeoutException:
            logger.warning("Activities request timed out")
            return []
        except httpx.ConnectError:
            logger.warning("Could not connect to activities API")
            return []
        except Exception as e:
            logger.warning(f"Error fetching activities: {e}")
            return []
    
    async def get_work_package_relations(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch work package relations for dependency analysis.
        
        Args:
            project_id: The OpenProject project ID
            
        Returns:
            List of relation dictionaries
            
        Raises:
            OpenProjectAPIError: If API request fails
        """
        # First get all work packages to then fetch their relations
        work_packages = await self.get_work_packages(project_id)
        relations = []
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                for wp in work_packages:
                    url = f"{self.base_url}/api/v3/work_packages/{wp.id}/relations"
                    logger.debug(f"Fetching relations for work package {wp.id}")
                    
                    response = await client.get(url, headers=self.headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "_embedded" in data and "elements" in data["_embedded"]:
                            relations.extend(data["_embedded"]["elements"])
                    elif response.status_code not in [404, 403]:  # 404/403 might be normal for some work packages
                        logger.warning(f"Failed to fetch relations for work package {wp.id}: {response.status_code}")
                
                logger.info(f"Successfully fetched {len(relations)} relations")
                return relations
                
        except httpx.TimeoutException:
            raise OpenProjectAPIError("Request to OpenProject API timed out", status_code=408)
        except httpx.ConnectError:
            raise OpenProjectAPIError("Could not connect to OpenProject API", status_code=503)
        except Exception as e:
            if isinstance(e, OpenProjectAPIError):
                raise
            raise OpenProjectAPIError(f"Unexpected error fetching relations: {str(e)}", status_code=500)
    
    async def get_time_entries(self, project_id: str) -> List[Dict[str, Any]]:
        """Fetch time entries for budget and resource analysis.
        
        Args:
            project_id: The OpenProject project ID
            
        Returns:
            List of time entry dictionaries
            
        Raises:
            OpenProjectAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v3/projects/{project_id}/time_entries"
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.info(f"Fetching time entries from: {url}")
                
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 401:
                    raise OpenProjectAPIError(
                        "Invalid API key or insufficient permissions", 
                        status_code=401
                    )
                elif response.status_code == 403:
                    raise OpenProjectAPIError(
                        "Insufficient permissions to access time entries", 
                        status_code=403
                    )
                elif response.status_code == 404:
                    logger.info("No time entries found for this project")
                    return []
                elif response.status_code != 200:
                    raise OpenProjectAPIError(
                        f"OpenProject API returned status {response.status_code}: {response.text}",
                        status_code=response.status_code
                    )
                
                data = response.json()
                time_entries = []
                
                if "_embedded" in data and "elements" in data["_embedded"]:
                    time_entries = data["_embedded"]["elements"]
                
                logger.info(f"Successfully fetched {len(time_entries)} time entries")
                return time_entries
                
        except httpx.TimeoutException:
            raise OpenProjectAPIError("Request to OpenProject API timed out", status_code=408)
        except httpx.ConnectError:
            raise OpenProjectAPIError("Could not connect to OpenProject API", status_code=503)
        except Exception as e:
            if isinstance(e, OpenProjectAPIError):
                raise
            raise OpenProjectAPIError(f"Unexpected error fetching time entries: {str(e)}", status_code=500)
    
    async def get_users(self) -> List[Dict[str, Any]]:
        """Fetch users for resource capacity analysis.
        
        Returns:
            List of user dictionaries
            
        Raises:
            OpenProjectAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v3/users"
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.info(f"Fetching users from: {url}")
                
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 401:
                    raise OpenProjectAPIError(
                        "Invalid API key or insufficient permissions", 
                        status_code=401
                    )
                elif response.status_code == 403:
                    raise OpenProjectAPIError(
                        "Insufficient permissions to access users", 
                        status_code=403
                    )
                elif response.status_code != 200:
                    raise OpenProjectAPIError(
                        f"OpenProject API returned status {response.status_code}: {response.text}",
                        status_code=response.status_code
                    )
                
                data = response.json()
                users = []
                
                if "_embedded" in data and "elements" in data["_embedded"]:
                    users = data["_embedded"]["elements"]
                
                logger.info(f"Successfully fetched {len(users)} users")
                return users
                
        except httpx.TimeoutException:
            raise OpenProjectAPIError("Request to OpenProject API timed out", status_code=408)
        except httpx.ConnectError:
            raise OpenProjectAPIError("Could not connect to OpenProject API", status_code=503)
        except Exception as e:
            if isinstance(e, OpenProjectAPIError):
                raise
            raise OpenProjectAPIError(f"Unexpected error fetching users: {str(e)}", status_code=500)
    
    async def get_work_package_journals(self, work_package_id: int) -> List[Dict[str, Any]]:
        """Fetch journals (activity/comments) for a work package.
        
        Args:
            work_package_id: The work package ID
            
        Returns:
            List of journal dictionaries
            
        Raises:
            OpenProjectAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v3/work_packages/{work_package_id}/activities"
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.debug(f"Fetching journals for work package {work_package_id}")
                
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 404:
                    logger.debug(f"No journals found for work package {work_package_id}")
                    return []
                elif response.status_code != 200:
                    logger.warning(f"Failed to fetch journals for work package {work_package_id}: {response.status_code}")
                    return []
                
                data = response.json()
                journals = []
                
                if "_embedded" in data and "elements" in data["_embedded"]:
                    journals = data["_embedded"]["elements"]
                
                return journals
                
        except Exception as e:
            logger.warning(f"Error fetching journals for work package {work_package_id}: {e}")
            return []
    
    async def get_work_package_attachments(self, work_package_id: int) -> List[Dict[str, Any]]:
        """Fetch attachments for a work package.
        
        Args:
            work_package_id: The work package ID
            
        Returns:
            List of attachment dictionaries
            
        Raises:
            OpenProjectAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v3/work_packages/{work_package_id}/attachments"
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                logger.debug(f"Fetching attachments for work package {work_package_id}")
                
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 404:
                    logger.debug(f"No attachments found for work package {work_package_id}")
                    return []
                elif response.status_code != 200:
                    logger.warning(f"Failed to fetch attachments for work package {work_package_id}: {response.status_code}")
                    return []
                
                data = response.json()
                attachments = []
                
                if "_embedded" in data and "elements" in data["_embedded"]:
                    attachments = data["_embedded"]["elements"]
                
                return attachments
                
        except Exception as e:
            logger.warning(f"Error fetching attachments for work package {work_package_id}: {e}")
            return []
    
    def _parse_work_package(self, wp_data: Dict[str, Any]) -> WorkPackage:
        """Parse work package data from OpenProject API response.
        
        Args:
            wp_data: Raw work package data from API
            
        Returns:
            WorkPackage object
        """
        # Log the complete work package data structure for debugging
        wp_id = wp_data.get('id', 'unknown')
        wp_subject = wp_data.get('subject', 'No Subject')
        
        logger.info(f"🔍 PARSING WORK PACKAGE {wp_id}: '{wp_subject}'")
        logger.debug(f"Complete work package data for WP {wp_id}: {wp_data}")
        
        # Log available keys to understand the structure
        available_keys = list(wp_data.keys())
        logger.info(f"Available keys in work package {wp_id}: {available_keys}")
        
        # Log key work package attributes for analysis context
        logger.info(f"WP {wp_id} basic info:")
        logger.info(f"  - Subject: '{wp_subject}'")
        logger.info(f"  - Created: {wp_data.get('createdAt', 'Unknown')}")
        logger.info(f"  - Updated: {wp_data.get('updatedAt', 'Unknown')}")
        logger.info(f"  - Due Date: {wp_data.get('dueDate', 'None')}")
        logger.info(f"  - Done Ratio: {wp_data.get('percentageDone', 'None')}%")
        
        # Extract status information with enhanced debugging and fallbacks
        # Check multiple locations: _embedded, direct field, and _links
        status = {}
        raw_status = None
        
        # First try to get status from _embedded section (individual work package fetch)
        if "_embedded" in wp_data and "status" in wp_data["_embedded"] and wp_data["_embedded"]["status"]:
            raw_status = wp_data["_embedded"]["status"]
            logger.info(f"Found status in _embedded for WP {wp_id}: {raw_status}")
        # Then try direct status field (bulk work package fetch)
        elif "status" in wp_data and wp_data["status"]:
            raw_status = wp_data["status"]
            logger.info(f"Found status in direct field for WP {wp_id}: {raw_status}")
        # Finally try _links section (common in query responses)
        elif "_links" in wp_data and "status" in wp_data["_links"] and wp_data["_links"]["status"]:
            raw_status = wp_data["_links"]["status"]
            logger.info(f"Found status in _links for WP {wp_id}: {raw_status}")
        
        if raw_status:
            # Extract ID from href if available
            status_id = None
            if "href" in raw_status and raw_status["href"]:
                href = raw_status["href"]
                if "/statuses/" in href:
                    status_id = href.split("/statuses/")[-1]
            
            status = {
                "id": raw_status.get("id") or status_id,
                "name": raw_status.get("name") or raw_status.get("title"),
                "href": raw_status.get("href")
            }
            
            # Validate status name and provide fallbacks
            if not status.get("name"):
                logger.warning(f"Work package {wp_id} has empty status name. Raw status: {raw_status}")
                # Try alternative fields that might contain status information
                if "title" in raw_status:
                    status["name"] = normalize_status_name(raw_status["title"])
                    logger.info(f"Using status title as fallback: {status['name']}")
                elif status_id:
                    status["name"] = f"Status-{status_id}"
                    logger.info(f"Generated status name from href: {status['name']}")
                else:
                    status["name"] = "Unknown Status"
                    logger.warning(f"Could not determine status name for WP {wp_id}, using fallback")
            else:
                # Normalize the status name for consistency
                original_name = status["name"]
                status["name"] = normalize_status_name(original_name)
                if original_name != status["name"]:
                    logger.info(f"Normalized status '{original_name}' to '{status['name']}' for WP {wp_id}")
        else:
            logger.warning(f"Work package {wp_id} has no status information in _embedded, direct field, or _links")
            status = {
                "id": None,
                "name": "No Status",
                "href": None
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
    
    def _parse_work_package_query_props(self, wp_data: Dict[str, Any]) -> WorkPackage:
        """Parse work package data from query_props format response.
        
        Args:
            wp_data: Raw work package data from query_props API
            
        Returns:
            WorkPackage object
        """
        wp_id = wp_data.get('id', 'unknown')
        wp_subject = wp_data.get('subject', 'No Subject')
        
        logger.info(f"🔍 PARSING WORK PACKAGE (QUERY_PROPS) {wp_id}: '{wp_subject}'")
        logger.debug(f"Complete work package data for WP {wp_id}: {wp_data}")
        
        # Log available keys to understand the structure
        available_keys = list(wp_data.keys())
        logger.info(f"Available keys in work package {wp_id}: {available_keys}")
        
        # Log key work package attributes for analysis context
        logger.info(f"WP {wp_id} basic info:")
        logger.info(f"  - Subject: '{wp_subject}'")
        logger.info(f"  - Created: {wp_data.get('createdAt', 'Unknown')}")
        logger.info(f"  - Updated: {wp_data.get('updatedAt', 'Unknown')}")
        logger.info(f"  - Due Date: {wp_data.get('dueDate', 'None')}")
        logger.info(f"  - Done Ratio: {wp_data.get('percentageDone', 'None')}%")
        
        # Extract status information - query_props format might be different
        status = self._extract_field_info(wp_data, "status", wp_id, "Status")
        
        # Extract type information
        type_info = self._extract_field_info(wp_data, "type", wp_id, "Type")
        
        # Extract priority information
        priority = self._extract_field_info(wp_data, "priority", wp_id, "Priority")
        
        # Extract assignee information
        assignee = self._extract_field_info(wp_data, "assignee", wp_id, "Assignee")
        
        # Log extracted field information
        logger.info(f"WP {wp_id} extracted fields:")
        logger.info(f"  - Status: {status.get('name', 'None') if status else 'None'}")
        logger.info(f"  - Type: {type_info.get('name', 'None') if type_info else 'None'}")
        logger.info(f"  - Priority: {priority.get('name', 'None') if priority else 'None'}")
        logger.info(f"  - Assignee: {assignee.get('name', 'None') if assignee else 'None'}")
        
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
    
    def _extract_field_info(self, wp_data: Dict[str, Any], field_name: str, wp_id: str, field_display_name: str) -> Optional[Dict[str, Any]]:
        """Extract field information from work package data with comprehensive debugging.
        
        Args:
            wp_data: Work package data
            field_name: Name of the field to extract (e.g., "status", "priority")
            wp_id: Work package ID for logging
            field_display_name: Display name for logging
            
        Returns:
            Field information dictionary or None
        """
        field_info = None
        raw_field = None
        
        # Try multiple possible locations for the field
        locations_to_try = [
            f"_embedded.{field_name}",
            field_name,
            f"{field_name}_id",
            f"{field_name}Name"
        ]
        
        # First try _embedded section
        if "_embedded" in wp_data and field_name in wp_data["_embedded"] and wp_data["_embedded"][field_name]:
            raw_field = wp_data["_embedded"][field_name]
            logger.info(f"Found {field_display_name} in _embedded for WP {wp_id}: {raw_field}")
        # Then try direct field
        elif field_name in wp_data and wp_data[field_name]:
            raw_field = wp_data[field_name]
            logger.info(f"Found {field_display_name} in direct field for WP {wp_id}: {raw_field}")
        # Try _links section (common in query responses)
        elif "_links" in wp_data and field_name in wp_data["_links"] and wp_data["_links"][field_name]:
            raw_field = wp_data["_links"][field_name]
            logger.info(f"Found {field_display_name} in _links for WP {wp_id}: {raw_field}")
        # Try as string value (query_props might return simple strings)
        elif field_name in wp_data and isinstance(wp_data[field_name], str):
            field_info = {
                "id": None,
                "name": wp_data[field_name],
                "href": None
            }
            logger.info(f"Found {field_display_name} as string for WP {wp_id}: '{wp_data[field_name]}'")
        
        if raw_field and isinstance(raw_field, dict):
            field_info = {
                "id": raw_field.get("id"),
                "name": raw_field.get("name"),
                "href": raw_field.get("href")
            }
            
            # Validate field name and provide fallbacks
            if not field_info.get("name"):
                logger.warning(f"Work package {wp_id} has empty {field_display_name} name. Raw {field_display_name}: {raw_field}")
                # Try alternative fields
                if "title" in raw_field:
                    field_info["name"] = raw_field["title"]
                    logger.info(f"Using {field_display_name} title as fallback: {field_info['name']}")
                elif "_links" in raw_field and "self" in raw_field["_links"]:
                    # Extract name from href if available
                    href = raw_field["_links"]["self"].get("href", "")
                    if f"/{field_name}s/" in href:
                        field_id = href.split(f"/{field_name}s/")[-1]
                        field_info["name"] = f"{field_display_name}-{field_id}"
                        logger.info(f"Generated {field_display_name} name from href: {field_info['name']}")
                else:
                    field_info["name"] = f"Unknown {field_display_name}"
                    logger.warning(f"Could not determine {field_display_name} name for WP {wp_id}, using fallback")
            else:
                # Normalize status names specifically
                if field_name == "status":
                    original_name = field_info["name"]
                    field_info["name"] = normalize_status_name(original_name)
                    if original_name != field_info["name"]:
                        logger.info(f"Normalized {field_display_name} '{original_name}' to '{field_info['name']}' for WP {wp_id}")
        elif not field_info:
            logger.warning(f"Work package {wp_id} has no {field_display_name} information")
            field_info = {
                "id": None,
                "name": f"No {field_display_name}",
                "href": None
            }
        
        return field_info
    
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
            async with httpx.AsyncClient(timeout=300.0) as client:
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
