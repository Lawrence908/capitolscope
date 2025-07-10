"""
Congress.gov API client for fetching congressional member data.

This module provides a client for interacting with the Congress.gov API
to fetch member profiles, biographical information, and legislative data.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import aiohttp
from pydantic import BaseModel, Field

from core.config import settings
from core.exceptions import ExternalAPIError, RateLimitError, NotFoundError
from core.logging import get_logger
from domains.base.interfaces import ExternalAPIInterface

logger = get_logger(__name__)


class CongressAPIConfig(BaseModel):
    """Configuration for Congress.gov API client."""
    
    base_url: str = Field(default="https://api.congress.gov/v3/")
    api_key: Optional[str] = Field(default=None)
    rate_limit_per_hour: int = Field(default=5000)  # Congress.gov API limit
    timeout: int = Field(default=30)
    retry_attempts: int = Field(default=3)
    retry_delay: float = Field(default=1.0)


class CongressAPIResponse(BaseModel):
    """Base response model for Congress.gov API."""
    
    request: Optional[Dict[str, Any]] = None
    pagination: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "allow"


class MemberResponse(CongressAPIResponse):
    """Response model for member data from Congress.gov API."""
    
    member: Optional[Dict[str, Any]] = None
    members: Optional[List[Dict[str, Any]]] = None


class CongressAPIClient(ExternalAPIInterface):
    """
    Client for Congress.gov API.
    
    Provides methods to fetch congressional member data, biographical information,
    and legislative activities with proper rate limiting and error handling.
    """
    
    def __init__(self, config: Optional[CongressAPIConfig] = None):
        """
        Initialize the Congress.gov API client.
        
        Args:
            config: API configuration. If None, uses default configuration.
        """
        self.config = config or CongressAPIConfig()
        
        # Use API key from settings if not provided in config
        if not self.config.api_key and settings.CONGRESS_GOV_API_KEY:
            self.config.api_key = settings.CONGRESS_GOV_API_KEY.get_secret_value()
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limiter = APIRateLimiter(self.config.rate_limit_per_hour)
        
        logger.info(f"Initialized Congress.gov API client with base URL: {self.config.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.authenticate()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def authenticate(self) -> bool:
        """
        Authenticate with the Congress.gov API.
        
        Returns:
            True if authentication is successful.
            
        Raises:
            ExternalAPIError: If authentication fails.
        """
        if not self.config.api_key:
            raise ExternalAPIError("Congress.gov API key not configured", api_name="congress.gov")
        
        # Create session with common headers
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "CapitolScope/1.0 (https://capitolscope.com)",
                "Accept": "application/json",
                "X-API-Key": self.config.api_key,
            }
        )
        
        # Test authentication with a simple request
        try:
            await self.get_member_list(limit=1)
            logger.info("Successfully authenticated with Congress.gov API")
            return True
        except Exception as e:
            logger.error(f"Failed to authenticate with Congress.gov API: {e}")
            raise ExternalAPIError(f"Authentication failed: {e}", api_name="congress.gov")
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None) -> Dict:
        """
        Make a request to the Congress.gov API.
        
        Args:
            endpoint: API endpoint path.
            method: HTTP method (GET, POST, etc.).
            params: Query parameters.
            
        Returns:
            API response data.
            
        Raises:
            RateLimitError: If rate limit is exceeded.
            ExternalAPIError: If API request fails.
        """
        if not self.session:
            await self.authenticate()
        
        # Check rate limit
        await self.rate_limiter.acquire()
        
        url = urljoin(self.config.base_url, endpoint)
        
        # Add format parameter for JSON response
        if not params:
            params = {}
        params["format"] = "json"
        
        # Retry logic
        for attempt in range(self.config.retry_attempts):
            try:
                if not self.session:
                    raise ExternalAPIError("Session not initialized", api_name="congress.gov")
                
                async with self.session.request(method, url, params=params) as response:
                    response_data = await response.json()
                    
                    if response.status == 200:
                        logger.debug(f"API request successful: {method} {url}")
                        return response_data
                    
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limit exceeded, retrying after {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    elif response.status == 404:
                        logger.warning(f"Resource not found: {url}")
                        raise NotFoundError("API endpoint", endpoint)
                    
                    else:
                        error_msg = f"API request failed with status {response.status}: {response_data}"
                        logger.error(error_msg)
                        raise ExternalAPIError(error_msg, api_name="congress.gov", status_code=response.status)
                        
            except aiohttp.ClientError as e:
                logger.error(f"HTTP client error on attempt {attempt + 1}: {e}")
                if attempt == self.config.retry_attempts - 1:
                    raise ExternalAPIError(f"HTTP client error: {e}", api_name="congress.gov")
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
            
            except asyncio.TimeoutError:
                logger.error(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.config.retry_attempts - 1:
                    raise ExternalAPIError("Request timeout", api_name="congress.gov")
                await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
        
        raise ExternalAPIError("Max retry attempts exceeded", api_name="congress.gov")
    
    async def handle_rate_limit(self) -> None:
        """Handle rate limiting by waiting if necessary."""
        await self.rate_limiter.wait_if_needed()
    
    # =======================================================================
    # MEMBER ENDPOINTS
    # =======================================================================
    
    async def get_member_list(self, limit: int = 20, offset: int = 0) -> MemberResponse:
        """
        Get a list of congressional members.
        
        Args:
            limit: Maximum number of members to return.
            offset: Number of members to skip.
            
        Returns:
            MemberResponse containing list of members.
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        response_data = await self.make_request("member", params=params)
        return MemberResponse(**response_data)
    
    async def get_member_by_bioguide_id(self, bioguide_id: str) -> MemberResponse:
        """
        Get detailed information for a specific member by bioguide ID.
        
        Args:
            bioguide_id: Member's bioguide ID.
            
        Returns:
            MemberResponse containing member details.
        """
        endpoint = f"member/{bioguide_id}"
        response_data = await self.make_request(endpoint)
        return MemberResponse(**response_data)
    
    async def get_members_by_state(self, state_code: str, limit: int = 20, offset: int = 0) -> MemberResponse:
        """
        Get members filtered by state.
        
        Args:
            state_code: Two-letter state code (e.g., 'CA', 'NY').
            limit: Maximum number of members to return.
            offset: Number of members to skip.
            
        Returns:
            MemberResponse containing filtered members.
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        endpoint = f"member/{state_code.upper()}"
        response_data = await self.make_request(endpoint, params=params)
        return MemberResponse(**response_data)
    
    async def get_members_by_state_and_district(self, state_code: str, district: str, limit: int = 20, offset: int = 0) -> MemberResponse:
        """
        Get members filtered by state and district.
        
        Args:
            state_code: Two-letter state code.
            district: District identifier.
            limit: Maximum number of members to return.
            offset: Number of members to skip.
            
        Returns:
            MemberResponse containing filtered members.
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        endpoint = f"member/{state_code.upper()}/{district}"
        response_data = await self.make_request(endpoint, params=params)
        return MemberResponse(**response_data)
    
    async def get_members_by_congress(self, congress_number: int, limit: int = 20, offset: int = 0) -> MemberResponse:
        """
        Get members by Congress number.
        
        Args:
            congress_number: Congress number (e.g., 118 for 118th Congress).
            limit: Maximum number of members to return.
            offset: Number of members to skip.
            
        Returns:
            MemberResponse containing members from specified Congress.
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        endpoint = f"member/congress/{congress_number}"
        response_data = await self.make_request(endpoint, params=params)
        return MemberResponse(**response_data)
    
    async def get_member_sponsored_legislation(self, bioguide_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get legislation sponsored by a specific member.
        
        Args:
            bioguide_id: Member's bioguide ID.
            limit: Maximum number of bills to return.
            offset: Number of bills to skip.
            
        Returns:
            Dictionary containing sponsored legislation data.
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        endpoint = f"member/{bioguide_id}/sponsored-legislation"
        return await self.make_request(endpoint, params=params)
    
    async def get_member_cosponsored_legislation(self, bioguide_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get legislation cosponsored by a specific member.
        
        Args:
            bioguide_id: Member's bioguide ID.
            limit: Maximum number of bills to return.
            offset: Number of bills to skip.
            
        Returns:
            Dictionary containing cosponsored legislation data.
        """
        params = {
            "limit": limit,
            "offset": offset
        }
        
        endpoint = f"member/{bioguide_id}/cosponsored-legislation"
        return await self.make_request(endpoint, params=params)
    
    # =======================================================================
    # UTILITY METHODS
    # =======================================================================
    
    async def search_members_by_name(self, name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for members by name.
        
        Args:
            name: Name to search for.
            limit: Maximum number of results to return.
            
        Returns:
            List of member dictionaries matching the search.
        """
        # Get all members and filter by name
        # Note: Congress.gov API doesn't have a direct search endpoint
        response = await self.get_member_list(limit=250)  # Get larger set to search
        
        if not response.members:
            return []
        
        # Filter members by name
        name_lower = name.lower()
        matching_members = []
        
        for member in response.members:
            member_name = member.get("name", "").lower()
            if name_lower in member_name:
                matching_members.append(member)
                if len(matching_members) >= limit:
                    break
        
        return matching_members
    
    async def get_current_congress_number(self) -> int:
        """
        Get the current Congress number.
        
        Returns:
            Current Congress number.
        """
        # Calculate based on current date
        # 118th Congress started January 3, 2023
        # Each Congress lasts 2 years
        import datetime
        
        base_year = 2023
        base_congress = 118
        current_year = datetime.datetime.now().year
        
        years_since_base = current_year - base_year
        congress_periods = years_since_base // 2
        
        return base_congress + congress_periods
    
    async def bulk_fetch_members(self, bioguide_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Fetch multiple members in bulk.
        
        Args:
            bioguide_ids: List of bioguide IDs to fetch.
            
        Returns:
            List of member data dictionaries.
        """
        members = []
        
        # Process in batches to respect rate limits
        batch_size = 10
        for i in range(0, len(bioguide_ids), batch_size):
            batch = bioguide_ids[i:i + batch_size]
            
            # Fetch members concurrently within batch
            tasks = [self.get_member_by_bioguide_id(bioguide_id) for bioguide_id in batch]
            
            try:
                batch_responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                for response in batch_responses:
                    if isinstance(response, Exception):
                        logger.warning(f"Failed to fetch member: {response}")
                        continue
                    
                    if isinstance(response, MemberResponse) and response.member:
                        members.append(response.member)
                
                # Small delay between batches
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in bulk fetch batch: {e}")
                continue
        
        return members


class APIRateLimiter:
    """Rate limiter for API requests."""
    
    def __init__(self, requests_per_hour: int):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_hour: Maximum requests per hour.
        """
        self.requests_per_hour = requests_per_hour
        self.requests_per_minute = requests_per_hour // 60
        self.request_times: List[datetime] = []
    
    async def acquire(self):
        """Acquire permission to make a request."""
        now = datetime.now()
        
        # Remove old request times (older than 1 hour)
        hour_ago = now - timedelta(hours=1)
        self.request_times = [t for t in self.request_times if t > hour_ago]
        
        # Check if we've hit the rate limit
        if len(self.request_times) >= self.requests_per_hour:
            # Wait until the oldest request is over an hour old
            oldest_request = min(self.request_times)
            wait_time = (oldest_request + timedelta(hours=1) - now).total_seconds()
            
            if wait_time > 0:
                logger.warning(f"Rate limit hit, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        # Record this request
        self.request_times.append(now)
    
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Count requests in the last minute
        recent_requests = [t for t in self.request_times if t > minute_ago]
        
        if len(recent_requests) >= self.requests_per_minute:
            # Wait until we're under the per-minute limit
            oldest_recent = min(recent_requests)
            wait_time = (oldest_recent + timedelta(minutes=1) - now).total_seconds()
            
            if wait_time > 0:
                logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)


# Create a singleton instance for easy access
_congress_api_client: Optional[CongressAPIClient] = None


async def get_congress_api_client() -> CongressAPIClient:
    """
    Get a singleton instance of the Congress API client.
    
    Returns:
        CongressAPIClient instance.
    """
    global _congress_api_client
    
    if _congress_api_client is None:
        _congress_api_client = CongressAPIClient()
        await _congress_api_client.authenticate()
    
    return _congress_api_client


async def close_congress_api_client():
    """Close the singleton Congress API client."""
    global _congress_api_client
    
    if _congress_api_client:
        await _congress_api_client.close()
        _congress_api_client = None


# Log client creation
logger.info("Congress.gov API client module initialized")
