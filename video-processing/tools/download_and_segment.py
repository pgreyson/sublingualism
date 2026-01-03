#!/usr/bin/env python3
import requests
import os
import subprocess
from dotenv import load_dotenv
from video_scene_detector import get_video_info

load_dotenv()

access_token = os.getenv('VIMEO_ACCESS_TOKEN')

def download_video(video_id, output_dir="videos"):
    """Download video from Vimeo"""
    headers = {
        'Authorization': f'bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get video info
    url = f'https://api.vimeo.com/videos/{video_id}'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error getting video info: {response.status_code}")
        return None
    
    data = response.json()
    video_name = data.get('name', 'Untitled')
    download_links = data.get('download', [])
    
    print(f"\nVideo: {video_name}")
    print(f"Download links available: {len(download_links)}")
    
    if not download_links:
        print("No download links available yet. Vimeo may still be processing.")
        return None
    
    # Show available qualities
    print("\nAvailable qualities:")
    for i, link in enumerate(download_links):
        print(f"{i+1}. {link.get('rendition', 'Unknown')} - {link.get('size_short', 'Unknown')} - {link.get('quality', 'Unknown')}")
    
    # Use the first HD or SD link
    download_url = None
    for link in download_links:
        if 'hd' in link.get('quality', '').lower() or 'sd' in link.get('quality', '').lower():
            download_url = link.get('link')
            quality = link.get('quality')
            size = link.get('size_short')
            break
    
    if not download_url and download_links:
        download_url = download_links[0].get('link')
        quality = download_links[0].get('quality', 'unknown')
        size = download_links[0].get('size_short', 'unknown')
    
    # Clean filename
    safe_name = "".join(c for c in video_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"{output_dir}/{video_id}_{safe_name}.mp4"
    
    print(f"\nDownloading {quality} quality ({size})...")
    print(f"Saving to: {filename}")
    
    # Download with progress
    response = requests.get(download_url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(filename, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    mb_downloaded = downloaded / (1024 * 1024)
                    mb_total = total_size / (1024 * 1024)
                    print(f"\rProgress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='')
    
    print(f"\n✓ Download complete!")
    return filename, video_name

# Test with one video
video_id = '1039553906'  # b0.0_c1.0_g1.0_l0.5_sbsl
print("Testing video download...")

result = download_video(video_id)
if result:
    video_path, video_name = result
    print(f"\nVideo downloaded to: {video_path}")
    
    # Check file
    if os.path.exists(video_path):
        file_size = os.path.getsize(video_path) / (1024 * 1024)
        print(f"File size: {file_size:.1f} MB")
        
        # Get video info with ffprobe
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                duration = float(info.get('format', {}).get('duration', 0))
                print(f"Duration: {duration:.1f}s ({duration//60:.0f}m {duration%60:.0f}s)")
                
                # Now we can do real scene detection!
                print("\nReady for scene detection!")
                print("Next steps:")
                print("1. Run actual ffmpeg scene detection")
                print("2. Generate accurate EDL based on visual analysis")
                print("3. Create VLC playlist with local file paths")
        except:
            print("ffprobe not found - install ffmpeg to analyze video")
else:
    print("\nCouldn't download video. Checking other videos...")
    
    # Try other videos
    other_videos = ['1093579689', '800192539']
    for vid in other_videos:
        info = get_video_info(vid)
        if info and info.get('download_links'):
            print(f"\n{info['name']} - {len(info['download_links'])} download links available")
        else:
            print(f"\nVideo {vid} - No downloads yet")