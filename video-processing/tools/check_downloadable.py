#!/usr/bin/env python3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

access_token = os.getenv('VIMEO_ACCESS_TOKEN')

video_ids = [
    '1039553906',  # b0.0_c1.0_g1.0_l0.5_sbsl
    '1093579689',  # charybdis  
    '800192539',   # synesthesia.mp4
]

headers = {
    'Authorization': f'bearer {access_token}',
    'Content-Type': 'application/json'
}

print("Checking download availability and updating settings...\n")

for video_id in video_ids:
    url = f'https://api.vimeo.com/videos/{video_id}'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        title = data.get('name', 'Untitled')
        download_links = data.get('download', [])
        privacy = data.get('privacy', {})
        
        print(f"{title} (ID: {video_id})")
        print(f"  Download links: {len(download_links)}")
        print(f"  Download enabled: {privacy.get('download', False)}")
        
        if not privacy.get('download', False):
            # Enable downloads
            update_data = {
                'privacy': {
                    'view': privacy.get('view', 'anybody'),
                    'embed': privacy.get('embed', 'public'),
                    'download': True,
                    'add': privacy.get('add', False)
                }
            }
            
            update_response = requests.patch(url, headers=headers, json=update_data)
            
            if update_response.status_code == 200:
                print(f"  ✓ Enabled downloads")
            else:
                print(f"  ✗ Failed to enable downloads: {update_response.status_code}")
        else:
            print(f"  ✓ Downloads already enabled")
        print()