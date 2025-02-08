#!/usr/bin/env python3

import sys
from typing import Dict, Any

from qingping_client import QingpingClient
from common import (
    TEMP_DIRECTORY, CLIENT_ID, CLIENT_SECRET,
    handle_error, validate_credentials, format_alfred_response
)

if sys.version_info < (3, 10):
    raise RuntimeError("This script requires Python 3.10 or higher")

def validate_args(mac: str, interval: int) -> None:
    """
    Validate input arguments.
    
    Args:
        mac: Device MAC address
        interval: Interval value in seconds
        
    Raises:
        ValueError: If arguments are invalid
    """
    if not mac:
        raise ValueError("MAC address is required")
    
    if interval < 60 or interval > 3600:
        raise ValueError("Interval must be between 60 and 3600 seconds")

def generate_success_response(mac: str, interval: int) -> list:
    """Generate success message items"""
    return [{
        'title': 'Settings updated successfully',
        'subtitle': f'Device {mac} intervals set to {interval} seconds'
    }]

def main():
    try:
        validate_credentials()

        if len(sys.argv) < 2:
            raise ValueError("Usage: update_device_settings.py <mac_address> <interval_seconds>")
            
        args = sys.argv[1].split()
        if len(args) != 2:
            raise ValueError("Arguments must be in the format: <mac_address> <interval_seconds>")
        
        mac_address = args[0]
        try:
            interval_seconds = int(args[1])
        except ValueError:
            raise ValueError("Interval must be a valid number")
        
        validate_args(mac_address, interval_seconds)

        client = QingpingClient(CLIENT_ID, CLIENT_SECRET, TEMP_DIRECTORY)
        client.update_device_settings(
            macs=[mac_address],
            collect_interval=interval_seconds,
            report_interval=interval_seconds
        )
        
        items = generate_success_response(mac_address, interval_seconds)
        print(format_alfred_response(items))
    except Exception as e:
        print(format_alfred_response(handle_error(e)['items']))

if __name__ == '__main__':
    main() 