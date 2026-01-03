#!/usr/bin/env python3
from video_scene_detector import analyze_video

# Analyze the 4-minute b0.0_c1.0_g1.0_l0.5_sbsl video
video_id = '1039553906'

print("Starting analysis of b0.0_c1.0_g1.0_l0.5_sbsl")
print("This is a 4-minute video, perfect for testing\n")

# Try with default scene detection (threshold 0.3)
edl_file, json_file = analyze_video(video_id, method='scene', threshold=0.3)