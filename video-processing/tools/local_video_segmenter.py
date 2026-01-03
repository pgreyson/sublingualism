#!/usr/bin/env python3
import subprocess
import json
import os
import sys
from generate_edl import create_edl, seconds_to_timecode

def detect_scenes_ffmpeg(video_path, threshold=0.3):
    """Use ffmpeg to detect scene changes"""
    print(f"\nAnalyzing: {video_path}")
    print(f"Scene detection threshold: {threshold}")
    print("Processing... (this may take a moment)")
    
    # Run scene detection
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-filter_complex',
        f"select='gt(scene,{threshold})',showinfo",
        '-f', 'null',
        '-'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse timestamps from output
    timestamps = []
    for line in result.stderr.split('\n'):
        if 'pts_time:' in line:
            # Extract timestamp
            try:
                pts_match = line.split('pts_time:')[1].split()[0]
                timestamp = float(pts_match)
                timestamps.append(timestamp)
            except:
                pass
    
    return sorted(timestamps)

def get_video_duration(video_path):
    """Get video duration using ffprobe"""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0

def segment_local_video(video_path, method='scene', threshold=0.3, interval=30):
    """Complete segmentation pipeline for local video"""
    
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        return
    
    # Get video info
    video_name = os.path.basename(video_path).rsplit('.', 1)[0]
    duration = get_video_duration(video_path)
    
    if duration == 0:
        print("Error: Could not determine video duration")
        return
    
    print(f"\nVideo: {video_name}")
    print(f"Duration: {duration:.1f}s ({duration//60:.0f}m {duration%60:.0f}s)")
    
    # Detect cut points based on method
    if method == 'scene':
        cut_points = detect_scenes_ffmpeg(video_path, threshold)
        print(f"\nDetected {len(cut_points)} scene changes")
    elif method == 'interval':
        cut_points = list(range(interval, int(duration), interval))
        print(f"\nCreated {len(cut_points)} intervals of {interval}s")
    else:
        print(f"Unknown method: {method}")
        return
    
    # Create output directory
    output_dir = f"segments_{video_name}_{method}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate EDL
    edl_content = create_edl(video_name, duration, cut_points)
    edl_filename = f"{output_dir}/{video_name}_{method}.edl"
    
    with open(edl_filename, 'w') as f:
        f.write(edl_content)
    print(f"\n✓ Created EDL: {edl_filename}")
    
    # Generate segments info
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
            "end_tc": seconds_to_timecode(end)
        })
    
    # Save JSON
    json_data = {
        "video_file": video_path,
        "video_name": video_name,
        "duration": duration,
        "method": method,
        "threshold": threshold if method == 'scene' else None,
        "interval": interval if method == 'interval' else None,
        "cut_points": cut_points,
        "segments": segments
    }
    
    json_filename = f"{output_dir}/{video_name}_{method}.json"
    with open(json_filename, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"✓ Created JSON: {json_filename}")
    
    # Create VLC playlist for local file
    playlist = ["#EXTM3U", f"#PLAYLIST:{video_name} - {method} segments", ""]
    
    for seg in segments:
        playlist.append(f"#EXTINF:{int(seg['duration'])},{video_name} - Segment {seg['index']+1}")
        playlist.append(f"#EXTVLCOPT:start-time={seg['start']}")
        playlist.append(f"#EXTVLCOPT:stop-time={seg['end']}")
        playlist.append(f"file://{os.path.abspath(video_path)}")
        playlist.append("")
    
    playlist_filename = f"{output_dir}/{video_name}_{method}.m3u"
    with open(playlist_filename, 'w') as f:
        f.write('\n'.join(playlist))
    print(f"✓ Created VLC playlist: {playlist_filename}")
    
    # Generate extraction script
    script = ["#!/bin/bash", f"# Extract segments from {video_name}", ""]
    script.append(f'INPUT="{os.path.abspath(video_path)}"')
    script.append(f'OUTPUT_DIR="{output_dir}/clips"')
    script.append('mkdir -p "$OUTPUT_DIR"')
    script.append("")
    
    for seg in segments:
        output_name = f"segment_{seg['index']+1:02d}_{seg['start']:.0f}-{seg['end']:.0f}s.mp4"
        script.append(f'echo "Extracting segment {seg["index"]+1}..."')
        script.append(f'ffmpeg -ss {seg["start"]} -i "$INPUT" -t {seg["duration"]} -c copy "$OUTPUT_DIR/{output_name}"')
        script.append("")
    
    script_filename = f"{output_dir}/extract_clips.sh"
    with open(script_filename, 'w') as f:
        f.write('\n'.join(script))
    os.chmod(script_filename, 0o755)
    print(f"✓ Created extraction script: {script_filename}")
    
    # Show summary
    print(f"\n📊 Summary:")
    print(f"   Total segments: {len(segments)}")
    if segments:
        durations = [s['duration'] for s in segments]
        print(f"   Average segment: {sum(durations)/len(durations):.1f}s")
        print(f"   Shortest: {min(durations):.1f}s")
        print(f"   Longest: {max(durations):.1f}s")
    
    print(f"\n📁 Output directory: {output_dir}/")
    print(f"\n🎬 To play in VLC:")
    print(f"   vlc {playlist_filename}")
    print(f"\n✂️  To extract clips:")
    print(f"   ./{script_filename}")
    
    return output_dir

# Main execution
if __name__ == "__main__":
    print("Local Video Segmenter")
    print("====================")
    
    if len(sys.argv) > 1:
        video_file = sys.argv[1]
        method = sys.argv[2] if len(sys.argv) > 2 else 'scene'
        
        if method == 'scene':
            threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.3
            segment_local_video(video_file, method='scene', threshold=threshold)
        elif method == 'interval':
            interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30
            segment_local_video(video_file, method='interval', interval=interval)
    else:
        print("\nUsage:")
        print("  python local_video_segmenter.py <video_file> [method] [options]")
        print("\nExamples:")
        print("  python local_video_segmenter.py video.mp4 scene 0.3")
        print("  python local_video_segmenter.py video.mp4 interval 30")
        print("\nMethods:")
        print("  scene [threshold] - Detect scene changes (default threshold: 0.3)")
        print("  interval [seconds] - Fixed intervals (default: 30s)")