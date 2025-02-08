#!/usr/bin/env python3

import sys
import time
from typing import Optional, List, Dict, Any

from qingping_client import QingpingClient
from common import (
    WORKFLOW_DIRECTORY, TEMP_DIRECTORY, CLIENT_ID, CLIENT_SECRET,
    handle_error, validate_credentials, format_alfred_response
)

if sys.version_info < (3, 10):
    raise RuntimeError("This script requires Python 3.10 or higher")

# Sensor thresholds
CO2_THRESHOLD_GREEN = 1000
CO2_THRESHOLD_YELLOW = 2000

PM25_THRESHOLD_GREEN = 12
PM25_THRESHOLD_YELLOW = 35

TVOC_THRESHOLD_GREEN = 220
TVOC_THRESHOLD_YELLOW = 660

HUMIDITY_THRESHOLD_GREEN_LOW = 40
HUMIDITY_THRESHOLD_GREEN_HIGH = 60
HUMIDITY_THRESHOLD_YELLOW_LOW = 20
HUMIDITY_THRESHOLD_YELLOW_HIGH = 80

TEMPERATURE_THRESHOLD_GREEN_LOW = 20
TEMPERATURE_THRESHOLD_GREEN_HIGH = 27
TEMPERATURE_THRESHOLD_YELLOW_LOW = 18
TEMPERATURE_THRESHOLD_YELLOW_HIGH = 32

def get_time_ago(timestamp: Optional[int]) -> str:
    """
    Convert timestamp to human readable time difference.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        str: Human readable time difference
    """
    if not timestamp:
        return 'Time unknown'
    
    now = int(time.time())
    if timestamp > now:
        return 'Just updated'
        
    diff = now - timestamp
    
    if diff < 60:
        return f'{diff} sec ago'
    elif diff < 3600:
        minutes = diff // 60
        return f'{minutes} min ago'
    elif diff < 86400:
        hours = diff // 3600
        return f'{hours} hr ago'
    else:
        days = diff // 86400
        return f'{days} days ago'

def choose_co2_icon(co2_value: int) -> str:
    """Select icon based on CO2 level"""
    if co2_value < CO2_THRESHOLD_GREEN:
        return f"{WORKFLOW_DIRECTORY}/icons/smile_green.png"
    elif CO2_THRESHOLD_GREEN <= co2_value < CO2_THRESHOLD_YELLOW:
        return f"{WORKFLOW_DIRECTORY}/icons/smile_yellow.png"
    else:
        return f"{WORKFLOW_DIRECTORY}/icons/sigh_red.png"

def choose_pm25_icon(pm25_value: int) -> str:
    """Select icon based on PM2.5 level"""
    if pm25_value < PM25_THRESHOLD_GREEN:
        return f"{WORKFLOW_DIRECTORY}/icons/smile_green.png"
    elif PM25_THRESHOLD_GREEN <= pm25_value < PM25_THRESHOLD_YELLOW:
        return f"{WORKFLOW_DIRECTORY}/icons/smile_yellow.png"
    else:
        return f"{WORKFLOW_DIRECTORY}/icons/sigh_red.png"

def choose_tvoc_icon(tvoc_value: int) -> str:
    """Select icon based on TVOC level"""
    if tvoc_value < TVOC_THRESHOLD_GREEN:
        return f"{WORKFLOW_DIRECTORY}/icons/smile_green.png"
    elif TVOC_THRESHOLD_GREEN <= tvoc_value < TVOC_THRESHOLD_YELLOW:
        return f"{WORKFLOW_DIRECTORY}/icons/smile_yellow.png"
    else:
        return f"{WORKFLOW_DIRECTORY}/icons/sigh_red.png"

def choose_humidity_icon(humidity_value: int) -> str:
    """Select icon based on humidity level"""
    if HUMIDITY_THRESHOLD_GREEN_LOW <= humidity_value < HUMIDITY_THRESHOLD_GREEN_HIGH:
        return f"{WORKFLOW_DIRECTORY}/icons/smile_green.png"
    elif (HUMIDITY_THRESHOLD_YELLOW_LOW <= humidity_value < HUMIDITY_THRESHOLD_GREEN_LOW or 
          HUMIDITY_THRESHOLD_GREEN_HIGH <= humidity_value < HUMIDITY_THRESHOLD_YELLOW_HIGH):
        return f"{WORKFLOW_DIRECTORY}/icons/smile_yellow.png"
    else:
        return f"{WORKFLOW_DIRECTORY}/icons/sigh_red.png"

def choose_temperature_icon(temperature_value: int) -> str:
    """Select icon based on temperature level"""
    if TEMPERATURE_THRESHOLD_GREEN_LOW <= temperature_value < TEMPERATURE_THRESHOLD_GREEN_HIGH:
        return f"{WORKFLOW_DIRECTORY}/icons/smile_green.png"
    elif (TEMPERATURE_THRESHOLD_YELLOW_LOW <= temperature_value < TEMPERATURE_THRESHOLD_GREEN_LOW or 
          TEMPERATURE_THRESHOLD_GREEN_HIGH <= temperature_value < TEMPERATURE_THRESHOLD_YELLOW_HIGH):
        return f"{WORKFLOW_DIRECTORY}/icons/smile_yellow.png"
    else:
        return f"{WORKFLOW_DIRECTORY}/icons/sigh_red.png"

def generate_items(devices: List[Dict[str, Any]]) -> list:
    """
    Generate formatted items for display.
    
    Args:
        devices: List of device data from API
        
    Returns:
        list: Formatted items for Alfred display
    """
    items = []
    for device in devices:
        name = device['info']['name']
        data = device['data']
        timestamp = data.get('timestamp', {}).get('value', None)
        human_readable_timestamp = get_time_ago(timestamp)

        sensors = {
            'co2': ('CO2 {value} ppm', choose_co2_icon),
            'pm25': ('PM2.5 {value} μg/m³', choose_pm25_icon),
            'tvoc': ('TVOC {value} ppb', choose_tvoc_icon),
            'humidity': ('Humidity {value} %', choose_humidity_icon),
            'temperature': ('Temperature {value} °C', choose_temperature_icon)
        }

        for key, (title_template, icon_func) in sensors.items():
            value = data.get(key, {}).get('value', None)
            if value is not None:
                items.append({
                    'title': title_template.format(value=value),
                    'subtitle': f'{name}, {human_readable_timestamp}',
                    'arg': f"{value}",
                    'icon': {
                        'path': icon_func(value)
                    }
                })
    return items

def main():
    try:
        validate_credentials()
        client = QingpingClient(CLIENT_ID, CLIENT_SECRET, TEMP_DIRECTORY)
        devices_response = client.get_devices()
        items = generate_items(devices_response['devices'])
        print(format_alfred_response(items))
    except Exception as e:
        print(format_alfred_response(handle_error(e)['items']))

if __name__ == '__main__':
    main()
