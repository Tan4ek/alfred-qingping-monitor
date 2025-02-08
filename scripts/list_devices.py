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

def generate_items(devices_response: Dict[str, Any]) -> list:
    """Generate formatted items for display"""
    items = []
    for device in devices_response['devices']:
        info = device['info']
        settings = info.get('setting', {})
        update_interval = settings.get('report_interval', 'Unknown interval')

        if update_interval < 60:
            interval_display = f"{update_interval} seconds"
        elif update_interval < 3600:
            minutes = update_interval // 60
            seconds = update_interval % 60
            interval_display = f"{minutes} minute(s) {seconds} second(s)" if seconds else f"{minutes} minute(s)"
        else:
            hours = update_interval // 3600
            minutes = (update_interval % 3600) // 60
            interval_display = f"{hours} hour(s) {minutes} minute(s)" if minutes else f"{hours} hour(s)"
        
        items.append({
            'title': info.get('name', 'Unnamed device'),
            'subtitle': f"MAC: {info.get('mac', 'Unknown MAC')}, Report data every: {interval_display}",
            'arg': info.get('mac', '')
        })
    
    if not items:
        items.append({
            'title': 'No devices found',
            'subtitle': 'Please check your device list in Qingping app',
            'valid': False
        })
    
    return items

def main():
    try:
        validate_credentials()
        client = QingpingClient(CLIENT_ID, CLIENT_SECRET, TEMP_DIRECTORY)
        devices_response = client.get_devices()
        items = generate_items(devices_response)
        print(format_alfred_response(items))
    except Exception as e:
        print(format_alfred_response(handle_error(e)['items']))

if __name__ == '__main__':
    main() 