#!/usr/bin/env python3

import os
import sys
import json
import logging
from typing import Dict, Any

# Common constants
WORKFLOW_DIRECTORY = '.'
TEMP_DIRECTORY = os.getenv("alfred_workflow_cache", "/tmp")
CLIENT_ID = os.getenv("CLEARGRASS_CLIENT_ID", '')
CLIENT_SECRET = os.getenv("CLEARGRASS_CLIENT_SECRET", '')

# Configure logging
logging.basicConfig(
    filename=os.path.join(TEMP_DIRECTORY, 'cleargrass.log'),
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def handle_error(error: Exception) -> Dict[str, Any]:
    """
    Format error message for display to user.
    
    Args:
        error: Exception that occurred
        
    Returns:
        Dict with formatted error message for Alfred
    """
    error_message = str(error)
    error_title = 'Error'
    
    if isinstance(error, ValueError):
        if "credentials" in str(error).lower():
            error_title = 'Configuration Error'
            error_message = 'Please set up CLEARGRASS_CLIENT_ID and CLEARGRASS_CLIENT_SECRET'
    
    logging.error(f"{error_title}: {error_message}", exc_info=True)
    
    return {
        'items': [{
            'title': error_title,
            'subtitle': error_message,
            'icon': {
                'path': f"{WORKFLOW_DIRECTORY}/icons/error.png"
            },
            'valid': False
        }]
    }

def validate_credentials() -> None:
    """
    Validate that required credentials are set.
    
    Raises:
        ValueError: If credentials are not configured
    """
    if not CLIENT_ID or not CLIENT_SECRET:
        raise ValueError("CLEARGRASS_CLIENT_ID and CLEARGRASS_CLIENT_SECRET are not configured")

def format_alfred_response(items: list) -> str:
    """
    Format response for Alfred workflow.
    
    Args:
        items: List of items to display
        
    Returns:
        JSON string formatted for Alfred
    """
    return json.dumps({'items': items}) 