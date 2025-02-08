#!/usr/bin/env python3

import sys
from typing import Dict, Any

from common import handle_error, format_alfred_response

if sys.version_info < (3, 10):
    raise RuntimeError("This script requires Python 3.10 or higher")

INTERVALS = [
    {"name": "1 minute", "seconds": 60},
    {"name": "5 minutes", "seconds": 300},
    {"name": "10 minutes", "seconds": 600},
    {"name": "1 hour", "seconds": 3600}
]

def generate_items(mac_address: str) -> list:
    """Generate formatted items for interval selection"""
    return [{
        'title': f"Set intervals to {interval['name']}",
        'subtitle': f"This will set the data collection and reporting intervals for the device with MAC address {mac_address}.",
        'arg': f"{mac_address} {interval['seconds']}"
    } for interval in INTERVALS]

def main():
    try:
        if len(sys.argv) < 2:
            raise ValueError("Device MAC address is required")
            
        mac_address = sys.argv[1]
        items = generate_items(mac_address)
        print(format_alfred_response(items))
    except Exception as e:
        print(format_alfred_response(handle_error(e)['items']))

if __name__ == '__main__':
    main() 