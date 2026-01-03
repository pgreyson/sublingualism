#!/usr/bin/env python3
import json
from generate_edl import create_edl, seconds_to_timecode

def create_interval_based_edl(video_name, video_id, duration, interval=30):
    """Create EDL based on fixed intervals without downloading"""
    print(f"\nGenerating EDL for: {video_name}")
    print(f"Duration: {duration}s ({duration//60}m {duration%60}s)")
    print(f"Interval: {interval}s")
    
    # Generate cut points at intervals
    cut_points = []
    current = interval
    while current < duration - 10:  # Stop 10s before end
        cut_points.append(current)
        current += interval
    
    print(f"Generated {len(cut_points)} cut points")
    
    # Create EDL
    edl_content = create_edl(video_name, duration, cut_points)
    edl_filename = f"{video_id}_interval_{interval}s.edl"
    
    with open(edl_filename, 'w') as f:
        f.write(edl_content)
    
    print(f"Created: {edl_filename}")
    
    # Create JSON with segment details
    segments = []
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
        
        segments.append({
            "index": i,
            "start": start,
            "end": end,
            "duration": end - start,
            "start_tc": seconds_to_timecode(start),
            "end_tc": seconds_to_timecode(end),
            "vimeo_url": f"https://vimeo.com/{video_id}#{int(start)}"
        })
    
    json_data = {
        "video_id": video_id,
        "video_name": video_name,
        "duration": duration,
        "interval": interval,
        "cut_points": cut_points,
        "segments": segments
    }
    
    json_filename = f"{video_id}_interval_{interval}s.json"
    with open(json_filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"Created: {json_filename}")
    
    # Show first few segments
    print(f"\nFirst 5 segments:")
    for seg in segments[:5]:
        print(f"  Segment {seg['index']}: {seg['start_tc']} - {seg['end_tc']} ({seg['duration']}s)")
    
    return edl_filename, json_filename

# Process several videos
videos = [
    {'id': '1039553906', 'name': 'b0.0_c1.0_g1.0_l0.5_sbsl', 'duration': 240},
    {'id': '1093579689', 'name': 'charybdis', 'duration': 1157},
    {'id': '800192539', 'name': 'synesthesia.mp4', 'duration': 196}
]

print("EDL Generation (Interval-Based)")
print("==============================")

for video in videos:
    create_interval_based_edl(video['name'], video['id'], video['duration'], interval=30)

print("\n\nTo use these EDL files:")
print("1. Import into your video editing software")
print("2. The software will create edit points at each timestamp")
print("3. You can then refine, delete, or rearrange segments")
print("\nThe JSON files contain the same data in a programmatic format")