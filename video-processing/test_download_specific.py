#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

access_token = os.getenv('VIMEO_ACCESS_TOKEN')

# Check the specific video you can download
video_id = '1093579689'  # charybdis

headers = {
    'Authorization': f'bearer {access_token}',
    'Content-Type': 'application/json'
}

# First, get the video details
print(f"Checking video {video_id}...")
url = f'https://api.vimeo.com/videos/{video_id}'

# Try with explicit fields
params = {
    'fields': 'uri,name,duration,download,privacy,play'
}

response = requests.get(url, headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    print(f"\nVideo: {data.get('name')}")
    print(f"Privacy settings: {data.get('privacy')}")
    print(f"Download array: {data.get('download')}")
    
    # Try the files endpoint
    print(f"\nTrying /videos/{video_id}/files endpoint...")
    files_url = f'https://api.vimeo.com/videos/{video_id}/files'
    files_response = requests.get(files_url, headers=headers)
    
    if files_response.status_code == 200:
        files_data = files_response.json()
        print(f"Files response: {files_data}")
    else:
        print(f"Files endpoint error: {files_response.status_code}")
        print(f"Response: {files_response.text[:200]}")
else:
    print(f"Error: {response.status_code}")
    print(response.text[:200])