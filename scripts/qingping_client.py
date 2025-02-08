#!/usr/bin/env python3

import http.client
import urllib.parse
import os
import base64
import json
import time
import logging
from http.client import HTTPException
from urllib.error import URLError
from socket import error as SocketError
from typing import Optional, Dict, Any, List

class QingpingClient:
    """
    Client for Qingping (Cleargrass) Cloud API.
    
    This client handles authentication and communication with the Qingping Cloud API,
    providing access to device data and measurements.
    """

    def __init__(self, client_id: str, client_secret: str, temp_directory: str):
        """
        Initialize Qingping API client.
        
        Args:
            client_id: OAuth client ID obtained from Qingping developer portal
            client_secret: OAuth client secret obtained from Qingping developer portal
            temp_directory: Directory for caching access tokens
            
        Raises:
            ValueError: If client_id or client_secret is missing
        """
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required")

        self._client_id = client_id
        self._client_secret = client_secret
        self._temp_directory = temp_directory
        self._oauth_host = 'oauth.cleargrass.com'
        self._api_host = 'apis.cleargrass.com'
        self._access_token = None
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self._temp_directory):
            os.makedirs(self._temp_directory)

    def get_devices(self) -> Dict[str, Any]:
        """
        Get list of user's devices and their latest data.
        
        Retrieves information about all devices associated with the account,
        including their latest sensor measurements.
        
        Returns:
            Dict[str, Any]: Response containing device list and their data
                Format:
                {
                    "devices": [
                        {
                            "info": {
                                "name": str,
                                "mac": str,
                                "type": str,
                                ...
                            },
                            "data": {
                                "temperature": {"value": float},
                                "humidity": {"value": float},
                                "co2": {"value": float},
                                "pm25": {"value": float},
                                "tvoc": {"value": float},
                                "timestamp": {"value": int}
                            }
                        },
                        ...
                    ]
                }
            
        Raises:
            Exception: On network or API errors
        """
        return self._make_api_request("GET", "/v1/apis/devices")

    def _make_api_request(self, method: str, path: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make an authenticated request to the Qingping API.
        
        Handles token management and request execution.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            payload: Optional request body data
            
        Returns:
            Dict[str, Any]: JSON response from the API
            
        Raises:
            Exception: On request or response errors
        """
        access_token = self._ensure_valid_token()
        
        conn = http.client.HTTPSConnection(self._api_host)
        try:
            headers = {
                'Authorization': f"Bearer {access_token}",
                'Content-Type': 'application/json'
            }
            
            if payload:
                body = json.dumps(payload)
            else:
                body = None
                
            conn.request(method, path, body, headers)
            return self._handle_response(conn.getresponse())
        finally:
            conn.close()

    def _handle_response(self, response) -> Dict[str, Any]:
        """
        Process HTTP response from the API.
        
        Args:
            response: HTTP response object
            
        Returns:
            Dict[str, Any]: Parsed JSON response if present, empty dict if no content
            
        Raises:
            Exception: On response errors
        """
        if response.status == 200:
            content_type = response.getheader('Content-Type')
            if not content_type:  # Empty response
                return {}
                
            if not content_type.startswith('application/json'):
                raise Exception(f"Unexpected Content-Type: {content_type}")
                
            data = response.read()
            try:
                return json.loads(data.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise Exception(f"Failed to decode JSON response: {e}")
        elif response.status == 401:
            # Token expired, reset and retry
            self._access_token = None
            return self.get_devices()
        else:
            raise Exception(f"API request failed. Status: {response.status}")

    def _ensure_valid_token(self) -> str:
        """
        Ensure a valid access token is available.
        
        Checks cache for valid token, fetches new one if needed.
        
        Returns:
            str: Valid access token
        """
        if not self._access_token:
            self._access_token = self._read_token_from_cache()
        
        if not self._access_token:
            token_response = self._fetch_new_token()
            self._access_token = token_response['access_token']
        
        return self._access_token

    def _read_token_from_cache(self) -> Optional[str]:
        """
        Read cached access token if still valid.
        
        Returns:
            Optional[str]: Valid cached token or None if not found/expired
        """
        cache_path = os.path.join(self._temp_directory, 'access_token_cache')
        try:
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as file:
                    for line in file.readlines():
                        try:
                            expired_at_time, access_token = line.strip().split(':')
                            if int(expired_at_time) > int(time.time()):
                                return access_token
                        except (ValueError, IndexError):
                            logging.warning("Invalid cache file format")
        except IOError as e:
            logging.error(f"Error reading cache file: {e}")
        return None

    def _save_token_to_cache(self, access_token: str, expired_at_time: int) -> None:
        """
        Save access token to cache file.
        
        Args:
            access_token: Token to cache
            expired_at_time: Token expiration timestamp
        """
        cache_path = os.path.join(self._temp_directory, 'access_token_cache')
        try:
            with open(cache_path, 'w') as file:
                file.write(f"{expired_at_time}:{access_token}")
        except IOError as e:
            logging.error(f"Error saving token to cache: {e}")

    def _fetch_new_token(self) -> Dict[str, Any]:
        """
        Fetch new access token from OAuth server.
        
        Performs client credentials OAuth flow to obtain new access token.
        
        Returns:
            Dict[str, Any]: Token response containing:
                {
                    "access_token": str,
                    "expires_in": int,
                    "token_type": "Bearer"
                }
            
        Raises:
            Exception: On authentication errors
        """
        conn = http.client.HTTPSConnection(self._oauth_host)
        try:
            payload = urllib.parse.urlencode({
                'grant_type': 'client_credentials',
                'scope': 'device_full_access'
            })
            auth = base64.b64encode(
                f"{self._client_id}:{self._client_secret}".encode()
            ).decode()
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {auth}'
            }
            
            conn.request("POST", "/oauth2/token", payload, headers)
            response = self._handle_response(conn.getresponse())
            
            if 'access_token' in response and 'expires_in' in response:
                expired_at_time = int(time.time()) + response['expires_in']
                self._save_token_to_cache(response['access_token'], expired_at_time)
                return response
            else:
                raise Exception("Invalid token response format")
        finally:
            conn.close()

    def update_device_settings(self, macs: List[str], collect_interval: Optional[int] = None, report_interval: Optional[int] = None) -> None:
        """
        Update settings for multiple devices.
        
        Args:
            macs: List of device MAC addresses
            collect_interval: Optional; Data collection interval in seconds (60-3600)
            report_interval: Optional; Data reporting interval in seconds (60-3600)
            
        Note:
            - collect_interval must be less than or equal to report_interval
            - Both intervals must be between 60 and 3600 seconds
            
        Returns:
            None: The API returns 200 status code with empty body on success
            
        Raises:
            ValueError: If intervals are invalid or no MAC addresses provided
            Exception: On network or API errors
        """
        if not macs:
            raise ValueError("At least one MAC address must be provided")
            
        if collect_interval is not None and (collect_interval < 60 or collect_interval > 3600):
            raise ValueError("collect_interval must be between 60 and 3600 seconds")
            
        if report_interval is not None and (report_interval < 60 or report_interval > 3600):
            raise ValueError("report_interval must be between 60 and 3600 seconds")
            
        if collect_interval is not None and report_interval is not None:
            if collect_interval > report_interval:
                raise ValueError("collect_interval must be less than or equal to report_interval")

        payload = {
            "mac": macs,
            "timestamp": int(time.time() * 1000)  # Current timestamp in milliseconds
        }
        
        if collect_interval is not None:
            payload['collect_interval'] = collect_interval
        if report_interval is not None:
            payload['report_interval'] = report_interval

        self._make_api_request(
            method="PUT",
            path="/v1/apis/devices/settings",
            payload=payload
        ) 