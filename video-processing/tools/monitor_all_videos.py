#!/usr/bin/env python3
import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

access_token = os.getenv('VIMEO_ACCESS_TOKEN')

def get_all_videos():
    """Get all videos from the account"""
    headers = {
        'Authorization': f'bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    url = 'https://api.vimeo.com/me/videos'
    params = {
        'per_page': 100,
        'fields': 'uri,name,duration,download,privacy'
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        videos = []
        
        for video in data.get('data', []):
            video_id = video['uri'].split('/')[-1]
            videos.append({
                'id': video_id,
                'name': video.get('name', 'Untitled'),
                'duration': video.get('duration', 0),
                'download_count': len(video.get('download', [])),
                'privacy': video.get('privacy', {})
            })
        
        return videos
    else:
        print(f"Error fetching videos: {response.status_code}")
        return []

def monitor_all_downloads():
    """Monitor all account videos for download availability"""
    print("Vimeo Account Download Monitor")
    print("==============================\n")
    
    check_count = 0
    
    while True:
        check_count += 1
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n[Check #{check_count}] {timestamp}")
        print("-" * 80)
        
        videos = get_all_videos()
        
        if not videos:
            print("No videos found or error accessing account")
            time.sleep(60)
            continue
        
        # Categorize videos
        ready = []
        not_ready = []
        
        for video in videos:
            if video['download_count'] > 0:
                ready.append(video)
            else:
                not_ready.append(video)
        
        # Display status
        print(f"\nTotal videos: {len(videos)}")
        print(f"Downloads ready: {len(ready)}")
        print(f"Not ready: {len(not_ready)}")
        
        if not_ready:
            print("\n⏳ Videos without downloads:")
            for v in not_ready:
                duration_min = v['duration'] / 60
                print(f"   - {v['name']} (ID: {v['id']}, {duration_min:.1f} min)")
        
        if ready:
            print("\n✅ Videos with downloads available:")
            for v in ready:
                duration_min = v['duration'] / 60
                print(f"   - {v['name']} (ID: {v['id']}, {duration_min:.1f} min, {v['download_count']} formats)")
        
        # Save current status
        with open('download_status.txt', 'w') as f:
            f.write(f"Status as of: {timestamp}\n")
            f.write(f"Total videos: {len(videos)}\n")
            f.write(f"Ready: {len(ready)}\n")
            f.write(f"Not ready: {len(not_ready)}\n\n")
            
            if ready:
                f.write("Ready for download:\n")
                for v in ready:
                    f.write(f"- {v['id']}: {v['name']}\n")
            
            if not_ready:
                f.write("\nStill processing:\n")
                for v in not_ready:
                    f.write(f"- {v['id']}: {v['name']}\n")
        
        # Check if there's been a change
        if check_count > 1 and ready:
            print("\n🔔 Downloads available! Check download_status.txt for details")
        
        # Wait before next check
        print(f"\nNext check in 60 seconds... (Press Ctrl+C to stop)")
        time.sleep(60)

if __name__ == "__main__":
    try:
        monitor_all_downloads()
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped by user")
        print("Check download_status.txt for the latest status")