#!/usr/bin/env python3
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os

def create_vlc_xspf_playlist(video_id, video_name, segments, video_url):
    """Create XSPF playlist for VLC with segment start/stop times"""
    
    # Create root element
    playlist = ET.Element('playlist')
    playlist.set('version', '1')
    playlist.set('xmlns', 'http://xspf.org/ns/0/')
    playlist.set('xmlns:vlc', 'http://www.videolan.org/vlc/playlist/ns/0/')
    
    # Add title
    title = ET.SubElement(playlist, 'title')
    title.text = f"{video_name} - Segments"
    
    # Create tracklist
    tracklist = ET.SubElement(playlist, 'trackList')
    
    # Add each segment as a track
    for seg in segments:
        track = ET.SubElement(tracklist, 'track')
        
        # Location (video URL)
        location = ET.SubElement(track, 'location')
        location.text = video_url
        
        # Title for this segment
        track_title = ET.SubElement(track, 'title')
        track_title.text = f"{video_name} - Segment {seg['index']+1} ({seg['start_tc']})"
        
        # Duration in milliseconds
        duration = ET.SubElement(track, 'duration')
        duration.text = str(int(seg['duration'] * 1000))
        
        # VLC extension for start/stop times
        extension = ET.SubElement(track, 'extension')
        extension.set('application', 'http://www.videolan.org/vlc/playlist/0')
        
        # Start time option
        vlc_option_start = ET.SubElement(extension, 'vlc:option')
        vlc_option_start.text = f"start-time={seg['start']}"
        
        # Stop time option
        vlc_option_stop = ET.SubElement(extension, 'vlc:option')
        vlc_option_stop.text = f"stop-time={seg['end']}"
    
    # Pretty print XML
    xml_str = ET.tostring(playlist, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding='UTF-8')
    
    return pretty_xml

def create_m3u_playlist(video_id, video_name, segments, video_url):
    """Create M3U playlist with VLC-specific timing options"""
    
    playlist_content = ["#EXTM3U"]
    playlist_content.append(f"#PLAYLIST:{video_name} - Segments")
    playlist_content.append("")
    
    for seg in segments:
        # Duration and title
        playlist_content.append(f"#EXTINF:{int(seg['duration'])},{video_name} - Segment {seg['index']+1}")
        
        # VLC-specific options
        playlist_content.append(f"#EXTVLCOPT:start-time={seg['start']}")
        playlist_content.append(f"#EXTVLCOPT:stop-time={seg['end']}")
        
        # Video URL
        playlist_content.append(video_url)
        playlist_content.append("")
    
    return "\n".join(playlist_content)

# Process existing JSON files
json_files = [
    '1039553906_interval_30s.json',
    '1093579689_interval_30s.json', 
    '800192539_interval_30s.json',
    '1039553906_scene_analysis_20260102_170349.json'
]

print("Creating VLC Playlists")
print("=====================\n")

for json_file in json_files:
    if os.path.exists(json_file):
        print(f"Processing: {json_file}")
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        video_id = data.get('video_id')
        video_name = data.get('video_name') or data.get('name')
        segments = data.get('segments', [])
        
        # Vimeo URL
        video_url = f"https://vimeo.com/{video_id}"
        
        # Create XSPF playlist
        xspf_content = create_vlc_xspf_playlist(video_id, video_name, segments, video_url)
        xspf_filename = json_file.replace('.json', '.xspf')
        
        with open(xspf_filename, 'wb') as f:
            f.write(xspf_content)
        
        print(f"  ✓ Created: {xspf_filename}")
        
        # Create M3U playlist
        m3u_content = create_m3u_playlist(video_id, video_name, segments, video_url)
        m3u_filename = json_file.replace('.json', '.m3u')
        
        with open(m3u_filename, 'w') as f:
            f.write(m3u_content)
        
        print(f"  ✓ Created: {m3u_filename}")
        print(f"  Segments: {len(segments)}")
        print()

print("\nHow to use these playlists:")
print("1. Open VLC")
print("2. File → Open File → Select .xspf or .m3u file")
print("3. VLC will play each segment with proper start/stop times")
print("\nNote: VLC may need network access to stream from Vimeo")
print("Some videos might require you to be logged into Vimeo")

# Create example local file playlist
print("\n\nExample: If you have local video files, here's the format:")
example_local = """#EXTM3U
#EXTINF:30,Local Video - Segment 1
#EXTVLCOPT:start-time=0
#EXTVLCOPT:stop-time=30
file:///Users/yourname/Videos/video.mp4

#EXTINF:30,Local Video - Segment 2  
#EXTVLCOPT:start-time=30
#EXTVLCOPT:stop-time=60
file:///Users/yourname/Videos/video.mp4
"""

with open('example_local_segments.m3u', 'w') as f:
    f.write(example_local)

print("Created: example_local_segments.m3u (template for local files)")