#!/usr/bin/env python3

import http.client
import urllib.parse
import os
import base64
import json
import sys
import time
import datetime
import logging
from http.client import HTTPException
from urllib.error import URLError
from socket import error as SocketError
from typing import Optional

if sys.version_info < (3, 10):
    raise RuntimeError("This script requires Python 3.10 or higher")

oauth_host = 'oauth.cleargrass.com'
api_host = 'apis.cleargrass.com'
temp_directory = os.getenv("alfred_workflow_cache", "/tmp")
workflow_directory = '.'

client_id = os.getenv("CLEARGRASS_CLIENT_ID", '')
client_secret = os.getenv("CLEARGRASS_CLIENT_SECRET", '')

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

# Настраиваем логирование
logging.basicConfig(
    filename=os.path.join(temp_directory, 'cleargrass.log'),
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def read_access_token_from_cache() -> Optional[str]:
    if not os.path.exists(temp_directory):
        os.makedirs(temp_directory)

    access_token_cache_filepath = os.path.join(temp_directory, 'access_token_cache')
    try:
        if os.path.exists(access_token_cache_filepath):
            with open(access_token_cache_filepath, 'r') as file:
                for line in file.readlines():
                    try:
                        expired_at_time, access_token = line.strip().split(':')
                        if int(expired_at_time) > int(time.time()):
                            return access_token
                    except (ValueError, IndexError):
                        logging.warning("Invalid cache file format")
                        return None
    except IOError as e:
        logging.error(f"Error reading cache file: {e}")
    return None

def save_access_token_to_cache(access_token: str, expired_at_time: int):
    if not os.path.exists(temp_directory):
        os.makedirs(temp_directory)

    access_token_cache_filepath = temp_directory + '/access_token_cache'
    with open(access_token_cache_filepath, 'w') as file:
        file.write(f"{expired_at_time}:{access_token}")

def get_access_token(client_id: str, client_secret: str) -> dict[str, any]:
    if not client_id or not client_secret:
        raise ValueError("Missing credentials (CLEARGRASS_CLIENT_ID or CLEARGRASS_CLIENT_SECRET)")
        
    conn = http.client.HTTPSConnection(oauth_host)
    try:
        payload = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'scope': 'device_full_access'
        })
        auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {auth}'
        }
        conn.request("POST", "/oauth2/token", payload, headers)
        res = conn.getresponse()
        data = res.read()
        if not res.getheader('Content-Type').startswith('application/json'):
            raise Exception(f"Unexpected Content-Type: {res.getheader('Content-Type')}")
        try:
            json_data = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to decode JSON response: {e}")
        if res.status == 200 and 'access_token' in json_data and 'expires_in' in json_data:
            access_token = json_data['access_token']
            expired_in_seconds = json_data['expires_in']
            expired_at_time = int(time.time()) + expired_in_seconds
            save_access_token_to_cache(access_token, expired_at_time)
            return {
                'access_token': access_token,
                'expires_in': expired_in_seconds,
                'expired_at_time': expired_at_time
            }
        else:
            response_status = res.status
            raise Exception(f"Failed to retrieve access token. {response_status} {json_data}")
    except (HTTPException, URLError, SocketError) as e:
        logging.error(f"Network connection error while getting token: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while getting token: {str(e)}")
        raise
    finally:
        conn.close()

def get_devices(access_token: str) -> dict[str, any]:
    if not access_token:
        raise ValueError("Missing access token")
        
    conn = http.client.HTTPSConnection(api_host)
    try:
        headers = {
            'Authorization': f"Bearer {access_token}"
        }
        conn.request("GET", "/v1/apis/devices", headers=headers)
        res = conn.getresponse()
        data = res.read()
        content_type = res.getheader('Content-Type')
        if content_type is None or not content_type.startswith('application/json'):
            raise Exception(f"Unexpected Content-Type: {content_type}")
        try:
            json_data = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to decode JSON response: {e}")
        if res.status == 200:
            return json_data
        elif res.status == 401:
            raise Exception(f"Unauthorized. {json_data}")
        else:
            response_status = res.status
            raise Exception(f"Failed to retrieve devices. {response_status} {json_data}")
    except (HTTPException, URLError, SocketError) as e:
        logging.error(f"Network connection error while getting devices: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error while getting devices: {str(e)}")
        raise
    finally:
        conn.close()

def choose_co2_icon(co2_value: int) -> str:
    if co2_value < CO2_THRESHOLD_GREEN:
        return workflow_directory + '/icons/smile_green.png'
    elif CO2_THRESHOLD_GREEN <= co2_value < CO2_THRESHOLD_YELLOW:
        return workflow_directory + '/icons/smile_yellow.png'
    else:
        return workflow_directory + '/icons/sigh_red.png'

def choose_pm25_icon(pm25_value: int) -> str:
    if pm25_value < PM25_THRESHOLD_GREEN:
        return workflow_directory + '/icons/smile_green.png'
    elif PM25_THRESHOLD_GREEN <= pm25_value < PM25_THRESHOLD_YELLOW:
        return workflow_directory + '/icons/smile_yellow.png'
    else:
        return workflow_directory + '/icons/sigh_red.png'

def choose_tvoc_icon(tvoc_value: int) -> str:
    if tvoc_value < TVOC_THRESHOLD_GREEN:
        return workflow_directory + '/icons/smile_green.png'
    elif TVOC_THRESHOLD_GREEN <= tvoc_value < TVOC_THRESHOLD_YELLOW:
        return workflow_directory + '/icons/smile_yellow.png'
    else:
        return workflow_directory + '/icons/sigh_red.png'

def choose_humidity_icon(humidity_value: int) -> str:
    if HUMIDITY_THRESHOLD_GREEN_LOW <= humidity_value < HUMIDITY_THRESHOLD_GREEN_HIGH:
        return workflow_directory + '/icons/smile_green.png'
    elif HUMIDITY_THRESHOLD_YELLOW_LOW <= humidity_value < HUMIDITY_THRESHOLD_GREEN_LOW or HUMIDITY_THRESHOLD_GREEN_HIGH <= humidity_value < HUMIDITY_THRESHOLD_YELLOW_HIGH:
        return workflow_directory + '/icons/smile_yellow.png'
    else:
        return workflow_directory + '/icons/sigh_red.png'

def choose_temperature_icon(temperature_value: int) -> str:
    if TEMPERATURE_THRESHOLD_GREEN_LOW <= temperature_value < TEMPERATURE_THRESHOLD_GREEN_HIGH:
        return workflow_directory + '/icons/smile_green.png'
    elif TEMPERATURE_THRESHOLD_YELLOW_LOW <= temperature_value < TEMPERATURE_THRESHOLD_GREEN_LOW or TEMPERATURE_THRESHOLD_GREEN_HIGH <= temperature_value < TEMPERATURE_THRESHOLD_YELLOW_HIGH:
        return workflow_directory + '/icons/smile_yellow.png'
    else:
        return workflow_directory + '/icons/sigh_red.png'

def get_time_ago(timestamp: Optional[int]) -> str:
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

def generate_items(devices: list) -> list:
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

def handle_error(error: Exception) -> dict:
    error_message = str(error)
    error_title = 'Network Error'
    
    if isinstance(error, (HTTPException, URLError, SocketError)):
        error_title = 'Network Connection Error'
        error_message = f'Please check your internet connection: {str(error)}'
    elif isinstance(error, json.JSONDecodeError):
        error_title = 'Data Processing Error'
        error_message = 'Invalid data received from server'
    elif isinstance(error, KeyError):
        error_title = 'Data Error'
        error_message = 'Missing required data in response'
    elif isinstance(error, ValueError):
        if "credentials" in str(error).lower():
            error_title = 'Configuration Error'
            error_message = 'Please set up CLEARGRASS_CLIENT_ID and CLEARGRASS_CLIENT_SECRET'
    
    logging.error(f"{error_title}: {error_message}", exc_info=True)
    
    return {
        'items': [{
            'title': error_title,
            'subtitle': error_message,
            'icon': {
                'path': workflow_directory + '/icons/error.png'
            },
            'valid': False
        }]
    }

try:
    if not client_id or not client_secret:
        raise ValueError("CLEARGRASS_CLIENT_ID and CLEARGRASS_CLIENT_SECRET are not configured")

    access_token = read_access_token_from_cache()
    if access_token is None:
        access_token_response = get_access_token(client_id, client_secret)
        access_token = access_token_response['access_token']
        expired_at_time = access_token_response['expired_at_time']
        save_access_token_to_cache(access_token, expired_at_time)

    devices_response = get_devices(access_token)
    devices = devices_response['devices']

    items = generate_items(devices)
    print(json.dumps({'items': items}))
except Exception as e:
    error_response = handle_error(e)
    print(json.dumps(error_response))
