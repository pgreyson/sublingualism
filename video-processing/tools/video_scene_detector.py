#!/usr/bin/env python3
import requests
import os
import subprocess
import json
from dotenv import load_dotenv
from generate_edl import create_edl, seconds_to_timecode

load_dotenv()

access_token = os.getenv('VIMEO_ACCESS_TOKEN')

def get_video_info(video_id):
    """Get video metadata and download link"""
    headers = {
        'Authorization': f'bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    url = f'https://api.vimeo.com/videos/{video_id}'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        return {
            'name': data.get('name', 'Untitled'),
            'duration': data.get('duration', 0),
            'download_links': data.get('download', [])
        }
    return None

def download_video(video_id, quality='sd'):
    """Download video from Vimeo"""
    info = get_video_info(video_id)
    if not info:
        print(f"Could not get info for video {video_id}")
        return None
    
    # Find download link
    download_url = None
    for link in info['download_links']:
        if quality in link.get('rendition', '').lower():
            download_url = link.get('link')
            break
    
    if not download_url and info['download_links']:
        # Use first available if quality not found
        download_url = info['download_links'][0].get('link')
    
    if not download_url:
        print(f"No download link available for {info['name']}")
        return None
    
    # Download file
    filename = f"{video_id}_{info['name']}.mp4".replace('/', '_')
    print(f"Downloading {info['name']}...")
    
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
                    print(f"\rProgress: {percent:.1f}%", end='')
    
    print(f"\nDownloaded to: {filename}")
    return filename, info

def detect_scenes(video_path, method='scene', threshold=0.3):
    """Detect scenes using different methods"""
    print(f"\nDetecting scenes using {method} method...")
    
    if method == 'scene':
        # Visual scene change detection
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-filter_complex',
            f"[0:v]select='gt(scene,{threshold})',showinfo[v]",
            '-map', '[v]',
            '-f', 'null',
            '-'
        ]
    elif method == 'silence':
        # Audio silence detection
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-af', 'silencedetect=noise=-30dB:d=0.5',
            '-f', 'null',
            '-'
        ]
    else:
        # Fixed interval
        return None
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse timestamps
    timestamps = []
    
    if method == 'scene':
        for line in result.stderr.split('\n'):
            if 'pts_time:' in line:
                parts = line.split('pts_time:')
                if len(parts) > 1:
                    timestamp = parts[1].split()[0]
                    timestamps.append(float(timestamp))
    elif method == 'silence':
        for line in result.stderr.split('\n'):
            if 'silence_start:' in line:
                parts = line.split('silence_start:')
                if len(parts) > 1:
                    timestamp = parts[1].split()[0]
                    timestamps.append(float(timestamp))
    
    return sorted(timestamps)

def analyze_video(video_id, method='scene', threshold=0.3):
    """Complete pipeline: download, analyze, create EDL"""
    print(f"\nAnalyzing video {video_id}")
    print("="*50)
    
    # Download video
    result = download_video(video_id, quality='sd')
    if not result:
        return
    
    video_path, info = result
    
    # Detect scenes
    if method == 'interval':
        # Fixed 30-second intervals
        timestamps = list(range(30, int(info['duration']), 30))
    else:
        timestamps = detect_scenes(video_path, method, threshold)
    
    print(f"\nFound {len(timestamps)} cut points")
    
    if timestamps:
        print("\nFirst 5 cut points:")
        for i, ts in enumerate(timestamps[:5]):
            print(f"  {i+1}. {seconds_to_timecode(ts)} ({ts:.2f}s)")
    
    # Create EDL
    edl_filename = f"{video_id}_{method}.edl"
    edl_content = create_edl(info['name'], info['duration'], timestamps)
    
    with open(edl_filename, 'w') as f:
        f.write(edl_content)
    
    print(f"\nCreated EDL: {edl_filename}")
    
    # Create JSON version
    json_filename = f"{video_id}_{method}.json"
    json_data = {
        "video_id": video_id,
        "name": info['name'],
        "duration": info['duration'],
        "method": method,
        "threshold": threshold if method == 'scene' else None,
        "cut_points": timestamps,
        "segments": []
    }
    
    # Add segments
    for i in range(len(timestamps) + 1):
        if i == 0:
            start = 0
            end = timestamps[0] if timestamps else info['duration']
        elif i == len(timestamps):
            start = timestamps[-1]
            end = info['duration']
        else:
            start = timestamps[i-1]
            end = timestamps[i]
        
        json_data["segments"].append({
            "index": i,
            "start": start,
            "end": end,
            "duration": end - start,
            "start_tc": seconds_to_timecode(start),
            "end_tc": seconds_to_timecode(end)
        })
    
    with open(json_filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Created JSON: {json_filename}")
    
    # Clean up video file if desired
    # os.remove(video_path)
    
    return edl_filename, json_filename

# Demo usage
if __name__ == "__main__":
    print("Video Scene Detection & EDL Generator")
    print("=====================================")
    print("\nAvailable methods:")
    print("1. scene - Detect visual scene changes")
    print("2. silence - Detect audio silence")
    print("3. interval - Fixed time intervals")
    
    # Example: analyze a short video
    # video_id = '1039553906'  # b0.0_c1.0_g1.0_l0.5_sbsl (4 minutes)
    # analyze_video(video_id, method='scene', threshold=0.3)