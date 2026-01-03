#!/usr/bin/env python3
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

access_token = os.getenv('VIMEO_ACCESS_TOKEN')

def check_download_status(video_ids):
    """Check if download links are available for videos"""
    headers = {
        'Authorization': f'bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"Checking download status at {datetime.now().strftime('%H:%M:%S')}")
    print("-" * 60)
    
    results = []
    for video_id in video_ids:
        url = f'https://api.vimeo.com/videos/{video_id}'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            name = data.get('name', 'Unknown')
            download_links = data.get('download', [])
            
            status = {
                'id': video_id,
                'name': name,
                'downloads_available': len(download_links) > 0,
                'link_count': len(download_links)
            }
            
            if download_links:
                print(f"✅ {name}: {len(download_links)} downloads ready")
                for link in download_links[:2]:  # Show first 2
                    print(f"   - {link.get('quality', 'Unknown')}: {link.get('size_short', 'Unknown')}")
            else:
                print(f"⏳ {name}: Not ready yet")
            
            results.append(status)
    
    return results

def monitor_downloads(video_ids, check_interval=60, max_checks=20):
    """Monitor videos until downloads are available"""
    print("Download Availability Monitor")
    print("============================\n")
    
    all_ready = False
    check_count = 0
    
    while not all_ready and check_count < max_checks:
        results = check_download_status(video_ids)
        
        ready_count = sum(1 for r in results if r['downloads_available'])
        all_ready = ready_count == len(video_ids)
        
        print(f"\nStatus: {ready_count}/{len(video_ids)} videos ready")
        
        if not all_ready:
            check_count += 1
            print(f"\nWaiting {check_interval} seconds before next check ({check_count}/{max_checks})...")
            time.sleep(check_interval)
            print("\n" + "="*60 + "\n")
        else:
            print("\n🎉 All videos have downloads available!")
            
            # Save ready status
            with open('downloads_ready.txt', 'w') as f:
                f.write(f"Downloads ready at: {datetime.now()}\n")
                for r in results:
                    f.write(f"{r['id']}: {r['name']} - {r['link_count']} links\n")
    
    if not all_ready:
        print(f"\n⚠️  Timeout: Not all videos ready after {max_checks} checks")
    
    return all_ready

# Video IDs to monitor
video_ids = [
    '1039553906',  # b0.0_c1.0_g1.0_l0.5_sbsl
    '1093579689',  # charybdis  
    '800192539',   # synesthesia.mp4
]

if __name__ == "__main__":
    # Quick check
    print("Quick check of current status:\n")
    check_download_status(video_ids)
    
    print("\n\nTo monitor continuously, run:")
    print("python check_vimeo_downloads.py monitor")
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'monitor':
        print("\n\nStarting continuous monitoring...\n")
        monitor_downloads(video_ids, check_interval=60, max_checks=20)