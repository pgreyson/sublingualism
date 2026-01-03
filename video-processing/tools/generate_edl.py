#!/usr/bin/env python3
import os
import subprocess
import json
from dotenv import load_dotenv

load_dotenv()

def analyze_video_scenes(video_path, threshold=0.3):
    """Use ffmpeg to detect scene changes and return timestamps"""
    print(f"Analyzing scenes in: {os.path.basename(video_path)}")
    
    # Use ffmpeg scene detection filter
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-filter:v', f"select='gt(scene,{threshold})',showinfo",
        '-f', 'null',
        '-'
    ]
    
    # Run ffmpeg and capture output
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse timestamps from ffmpeg output
    timestamps = []
    for line in result.stderr.split('\n'):
        if 'pts_time:' in line:
            # Extract timestamp
            parts = line.split('pts_time:')
            if len(parts) > 1:
                timestamp = parts[1].split()[0]
                timestamps.append(float(timestamp))
    
    return sorted(timestamps)

def create_edl(video_name, duration, cut_points, fps=30):
    """Create an EDL file from cut points"""
    edl_content = []
    
    # EDL header
    edl_content.append("TITLE: " + video_name)
    edl_content.append("FCM: NON-DROP FRAME")
    edl_content.append("")
    
    # Add cuts
    for i, cut_time in enumerate(cut_points):
        if i == 0:
            start_time = 0
        else:
            start_time = cut_points[i-1]
        
        end_time = cut_time
        
        # Convert to timecode (assuming 30fps)
        start_tc = seconds_to_timecode(start_time, fps)
        end_tc = seconds_to_timecode(end_time, fps)
        
        # EDL format: EDIT# REEL AUD TRANS DUR    SRC_IN     SRC_OUT    REC_IN     REC_OUT
        edit_num = str(i + 1).zfill(3)
        edl_content.append(f"{edit_num}  001  V  C        {start_tc} {end_tc} {start_tc} {end_tc}")
    
    # Add final segment
    if cut_points:
        last_cut = cut_points[-1]
        start_tc = seconds_to_timecode(last_cut, fps)
        end_tc = seconds_to_timecode(duration, fps)
        edit_num = str(len(cut_points) + 1).zfill(3)
        edl_content.append(f"{edit_num}  001  V  C        {start_tc} {end_tc} {start_tc} {end_tc}")
    
    return '\n'.join(edl_content)

def seconds_to_timecode(seconds, fps=30):
    """Convert seconds to timecode format HH:MM:SS:FF"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    frames = int((seconds % 1) * fps)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frames:02d}"

def create_demo_edl():
    """Create a demo EDL to show the format"""
    print("\nDemo EDL Format:")
    print("================")
    
    # Sample data
    video_name = "charybdis"
    duration = 1157  # 19m 17s
    
    # Generate cut points every 60 seconds with some variation
    cut_points = []
    current = 60
    while current < duration - 60:
        cut_points.append(current)
        # Add some variation to make it more natural
        current += 60 + (hash(str(current)) % 20 - 10)
    
    edl = create_edl(video_name, duration, cut_points)
    
    # Save demo
    with open('demo_charybdis.edl', 'w') as f:
        f.write(edl)
    
    print(edl[:500] + "...")
    print(f"\nCreated demo_charybdis.edl with {len(cut_points)} cut points")
    
    # Also create a JSON version for easier parsing
    json_data = {
        "video": video_name,
        "duration": duration,
        "fps": 30,
        "cuts": cut_points,
        "segments": []
    }
    
    # Add segment data
    for i in range(len(cut_points) + 1):
        if i == 0:
            start = 0
            end = cut_points[0] if cut_points else duration
        elif i == len(cut_points):
            start = cut_points[-1]
            end = duration
        else:
            start = cut_points[i-1]
            end = cut_points[i]
        
        json_data["segments"].append({
            "index": i,
            "start": start,
            "end": end,
            "duration": end - start
        })
    
    with open('demo_charybdis.json', 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Also created demo_charybdis.json for programmatic access")

if __name__ == "__main__":
    create_demo_edl()
    
    print("\n\nTo use with actual videos:")
    print("1. Download video from Vimeo")
    print("2. Run scene detection with adjustable threshold")
    print("3. Generate EDL with detected cut points")
    print("\nEDL files can be imported into:")
    print("- Adobe Premiere Pro")
    print("- Final Cut Pro")
    print("- DaVinci Resolve")
    print("- Most professional editing software")