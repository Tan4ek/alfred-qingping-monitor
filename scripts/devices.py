#!/usr/bin/env python3

import http.client
import urllib.parse
import os
import base64
import json
import sys
import time

oauth_host = 'oauth.cleargrass.com'
api_host = 'apis.cleargrass.com'
temp_directory = os.getenv("alfred_workflow_cache", "/tmp")
workflow_directory = os.getenv("alfred_workflow_data", os.path.expanduser("~/Library/Application Support/Alfred/Workflow Data/com.alfredapp.clear-grass"))

client_id = os.getenv("CLEARGRASS_CLIENT_ID", '')
client_secret = os.getenv("CLEARGRASS_CLIENT_SECRET", '')

def read_access_token_from_cache() -> str | None:
    if not os.path.exists(temp_directory):
        os.makedirs(temp_directory)

    # read the access token cache file
    access_token_cache_filepath = temp_directory + '/access_token_cache'
    if os.path.exists(access_token_cache_filepath):
        with open(access_token_cache_filepath, 'r') as file:
            # read line by line , split by ':' and create a dict
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


access_token = read_access_token_from_cache()
if access_token is None:
    access_token_respons = get_access_token(client_id, client_secret)
    access_token = access_token_respons['access_token']
    expired_at_time = access_token_respons['expired_at_time']
    save_access_token_to_cache(access_token, expired_at_time)

try:
    devices_response = get_devices(access_token)
    devices = devices_response['devices']
    items = []
    for device in devices:
        name = device['info']['name']
        data = device['data']
        co2 = data['co2']['value']
        pm25 = data['pm25']['value']
        tvoc = data['tvoc']['value']
        humidity = data['humidity']['value']
        timestamp = data['timestamp']['value'] # unix epoch seconds
        items.append({
            'title': f'CO2 {co2}',
            'subtitle' : f'{name}',
            'arg': f"{co2}",
            'icon': workflow_directory +'/icons/air-quality.png'
        })
        items.append({
            'title': f'PM2.5 {pm25}',
            'subtitle' : f'{name}',
            'arg': f"{pm25}",
            'icon': workflow_directory +'/icons/air-pollution.png'
        })
        items.append({
            'title': f'TVOC {tvoc}',
            'subtitle' : f'{name}',
            'arg': f"{tvoc}",
            'icon': workflow_directory+'/icons/voc.png'
        })
        items.append({
            'title': f'Humidity {humidity}',
            'subtitle' : f'{name}',
            'arg': f"{humidity}",
            'icon': workflow_directory+'/icons/humidity.png'
        })
    print(json.dumps({'items': items}))
except Exception as e:
    print(f"Failed to get devices: {e}")
