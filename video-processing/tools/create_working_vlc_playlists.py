#!/usr/bin/env python3
import json
import os

def create_vlc_playlist_with_notes(video_id, video_name, segments):
    """Create VLC playlist with instructions for manual use"""
    
    playlist_content = ["#EXTM3U"]
    playlist_content.append(f"#PLAYLIST:{video_name} - Segments")
    playlist_content.append("")
    
    # Add instructions as a comment
    playlist_content.append("# INSTRUCTIONS:")
    playlist_content.append("# 1. Download the video from Vimeo first")
    playlist_content.append("# 2. Replace 'file:///path/to/your/video.mp4' with actual path")
    playlist_content.append("# 3. Or use VLC's 'Open Network Stream' with Vimeo video page URL")
    playlist_content.append("")
    
    # Create entries for local file (user needs to update path)
    example_path = f"file:///Users/paul/Videos/{video_name}.mp4"
    
    for seg in segments:
        # Duration and title
        playlist_content.append(f"#EXTINF:{int(seg['duration'])},{video_name} - Segment {seg['index']+1} [{seg['start_tc']} - {seg['end_tc']}]")
        
        # VLC-specific options
        playlist_content.append(f"#EXTVLCOPT:start-time={seg['start']}")
        playlist_content.append(f"#EXTVLCOPT:stop-time={seg['end']}")
        
        # File path (user needs to update)
        playlist_content.append(example_path)
        playlist_content.append("")
    
    return "\n".join(playlist_content)

def create_ffmpeg_commands(video_id, video_name, segments):
    """Create ffmpeg commands to extract segments"""
    
    commands = []
    commands.append("#!/bin/bash")
    commands.append(f"# Extract segments from {video_name}")
    commands.append("# First download the video, then run these commands")
    commands.append("")
    commands.append(f"INPUT_VIDEO=\"{video_name}.mp4\"")
    commands.append("OUTPUT_DIR=\"segments\"")
    commands.append("mkdir -p $OUTPUT_DIR")
    commands.append("")
    
    for seg in segments:
        output_name = f"{video_id}_segment_{seg['index']+1:02d}.mp4"
        duration = seg['duration']
        
        # FFmpeg command to extract segment
        cmd = f"ffmpeg -ss {seg['start']} -i \"$INPUT_VIDEO\" -t {duration} -c copy \"$OUTPUT_DIR/{output_name}\""
        commands.append(f"echo \"Extracting segment {seg['index']+1}...\"")
        commands.append(cmd)
        commands.append("")
    
    return "\n".join(commands)

# Process JSON files
json_files = ['1039553906_interval_30s.json']

print("Creating Working VLC Playlists")
print("==============================\n")

for json_file in json_files:
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        video_id = data.get('video_id')
        video_name = data.get('video_name') or data.get('name')
        segments = data.get('segments', [])
        
        # Create playlist for local files
        playlist_content = create_vlc_playlist_with_notes(video_id, video_name, segments)
        playlist_filename = f"{video_id}_local.m3u"
        
        with open(playlist_filename, 'w') as f:
            f.write(playlist_content)
        
        print(f"Created: {playlist_filename}")
        
        # Create extraction script
        script_content = create_ffmpeg_commands(video_id, video_name, segments)
        script_filename = f"extract_segments_{video_id}.sh"
        
        with open(script_filename, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_filename, 0o755)
        print(f"Created: {script_filename}")

print("\n\nWorkaround Options:")
print("===================")
print("\n1. Manual VLC Method:")
print("   - Open VLC")
print("   - Go to Media → Open Network Stream")
print("   - Enter: https://vimeo.com/1039553906")
print("   - After video loads, use Playback → Jump to Time")
print("   - Jump to times from the JSON files")

print("\n2. Download First Method:")
print("   - Download video from Vimeo to your computer")
print("   - Edit the _local.m3u playlist to update the file path")
print("   - Open the edited playlist in VLC")

print("\n3. Extract Segments Method:")
print("   - Download video from Vimeo")
print("   - Run: ./extract_segments_1039553906.sh")
print("   - This will create individual video files for each segment")

# Create a simple segment list
with open('segment_times.txt', 'w') as f:
    f.write("Video Segment Times\n")
    f.write("==================\n\n")
    
    for json_file in ['1039553906_interval_30s.json', '1039553906_scene_analysis_20260102_170349.json']:
        if os.path.exists(json_file):
            with open(json_file, 'r') as jf:
                data = json.load(jf)
            
            f.write(f"{data.get('video_name', 'Unknown')} - {json_file}\n")
            f.write("-" * 50 + "\n")
            
            for seg in data.get('segments', [])[:10]:  # First 10 segments
                f.write(f"Segment {seg['index']+1}: {seg['start_tc']} - {seg['end_tc']} ({seg['duration']}s)\n")
            
            if len(data.get('segments', [])) > 10:
                f.write(f"... and {len(data['segments']) - 10} more segments\n")
            
            f.write("\n")

print("\nCreated: segment_times.txt (for manual reference)")