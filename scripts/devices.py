#!/usr/bin/env python3

import http.client
import urllib.parse
import os
import base64
import json
import sys
import time
import datetime

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

def read_access_token_from_cache() -> str | None:
    if not os.path.exists(temp_directory):
        os.makedirs(temp_directory)

    access_token_cache_filepath = temp_directory + '/access_token_cache'
    if os.path.exists(access_token_cache_filepath):
        with open(access_token_cache_filepath, 'r') as file:
            for line in file.readlines():
                parts = line.split(':')
                expired_at_time = int(parts[0].strip())
                access_toke = parts[1].strip()
                # linux epoch secons now
                now = int(time.time())
                if expired_at_time > now:
                    return access_toke
            return None
    else:
        return None

def save_access_token_to_cache(access_token: str, expired_at_time: int):
    if not os.path.exists(temp_directory):
        os.makedirs(temp_directory)

    access_token_cache_filepath = temp_directory + '/access_token_cache'
    with open(access_token_cache_filepath, 'w') as file:
        file.write(f"{expired_at_time}:{access_token}")

def get_access_token(client_id: str, client_secret: str) -> dict[str, any]:
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
    finally:
        conn.close()

def get_devices(access_token: str) -> dict[str, any]:
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

def generate_items(devices: list) -> list:
    items = []
    for device in devices:
        name = device['info']['name']
        data = device['data']
        timestamp = data.get('timestamp', {}).get('value', None)
        human_readable_timestamp = datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S %d.%m.%Y') if timestamp else 'Unknown time'

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

access_token = read_access_token_from_cache()
if access_token is None:
    access_token_respons = get_access_token(client_id, client_secret)
    access_token = access_token_respons['access_token']
    expired_at_time = access_token_respons['expired_at_time']
    save_access_token_to_cache(access_token, expired_at_time)

try:
    devices_response = get_devices(access_token)
    devices = devices_response['devices']

    items = generate_items(devices)
    print(json.dumps({'items': items}))
except Exception as e:
    print(f"Failed to get devices: {e}")
