#!/bin/bash
# Extract segments from charybdis_v2 (1080p)

INPUT="/Volumes/Workspace/Downloads/charybdis_v2 (1080p).mp4"
OUTPUT_DIR="segments_charybdis_v2 (1080p)_scene/clips"
mkdir -p "$OUTPUT_DIR"

echo "Extracting segment 1..."
ffmpeg -ss 0 -i "$INPUT" -t 430.1 -c copy "$OUTPUT_DIR/segment_01_0-430s.mp4"

echo "Extracting segment 2..."
ffmpeg -ss 430.1 -i "$INPUT" -t 338.3333329999999 -c copy "$OUTPUT_DIR/segment_02_430-768s.mp4"

echo "Extracting segment 3..."
ffmpeg -ss 768.433333 -i "$INPUT" -t 389.06666700000005 -c copy "$OUTPUT_DIR/segment_03_768-1158s.mp4"
