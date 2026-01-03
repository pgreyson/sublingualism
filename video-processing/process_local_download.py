#!/usr/bin/env python3
import os
import glob
from tools.local_video_segmenter import segment_local_video

# Common download locations
possible_paths = [
    "~/Downloads/*.mp4",
    "~/Downloads/*.mov",
    "~/Desktop/*.mp4",
    "~/Desktop/*.mov",
    "/Volumes/*/Downloads/*.mp4",
    "charybdis*.mp4",
    "*1093579689*.mp4"
]

print("Looking for downloaded videos...")
print("=" * 50)

found_videos = []
for pattern in possible_paths:
    expanded = os.path.expanduser(pattern)
    matches = glob.glob(expanded)
    found_videos.extend(matches)

if found_videos:
    print(f"\nFound {len(found_videos)} video file(s):")
    for i, video in enumerate(found_videos):
        size_mb = os.path.getsize(video) / (1024 * 1024)
        print(f"{i+1}. {os.path.basename(video)} ({size_mb:.1f} MB)")
        print(f"   Path: {video}")
    
    print("\nTo segment a video, run:")
    print(f"python tools/local_video_segmenter.py '{found_videos[0]}' scene 0.3")
else:
    print("\nNo videos found in common download locations.")
    print("\nAfter downloading from Vimeo:")
    print("1. Note where you saved the file")
    print("2. Run: python tools/local_video_segmenter.py /path/to/video.mp4 scene 0.3")

print("\nAlternatively, drag and drop the video file into Terminal after typing:")
print("python tools/local_video_segmenter.py ")