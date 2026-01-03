#!/bin/bash
# Extract segments from charybdis_v2 (1080p)

INPUT="/Volumes/Workspace/Downloads/charybdis_v2 (1080p).mp4"
OUTPUT_DIR="segments_charybdis_v2 (1080p)_interval/clips"
mkdir -p "$OUTPUT_DIR"

echo "Extracting segment 1..."
ffmpeg -ss 0 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_01_0-60s.mp4"

echo "Extracting segment 2..."
ffmpeg -ss 60 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_02_60-120s.mp4"

echo "Extracting segment 3..."
ffmpeg -ss 120 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_03_120-180s.mp4"

echo "Extracting segment 4..."
ffmpeg -ss 180 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_04_180-240s.mp4"

echo "Extracting segment 5..."
ffmpeg -ss 240 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_05_240-300s.mp4"

echo "Extracting segment 6..."
ffmpeg -ss 300 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_06_300-360s.mp4"

echo "Extracting segment 7..."
ffmpeg -ss 360 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_07_360-420s.mp4"

echo "Extracting segment 8..."
ffmpeg -ss 420 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_08_420-480s.mp4"

echo "Extracting segment 9..."
ffmpeg -ss 480 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_09_480-540s.mp4"

echo "Extracting segment 10..."
ffmpeg -ss 540 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_10_540-600s.mp4"

echo "Extracting segment 11..."
ffmpeg -ss 600 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_11_600-660s.mp4"

echo "Extracting segment 12..."
ffmpeg -ss 660 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_12_660-720s.mp4"

echo "Extracting segment 13..."
ffmpeg -ss 720 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_13_720-780s.mp4"

echo "Extracting segment 14..."
ffmpeg -ss 780 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_14_780-840s.mp4"

echo "Extracting segment 15..."
ffmpeg -ss 840 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_15_840-900s.mp4"

echo "Extracting segment 16..."
ffmpeg -ss 900 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_16_900-960s.mp4"

echo "Extracting segment 17..."
ffmpeg -ss 960 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_17_960-1020s.mp4"

echo "Extracting segment 18..."
ffmpeg -ss 1020 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_18_1020-1080s.mp4"

echo "Extracting segment 19..."
ffmpeg -ss 1080 -i "$INPUT" -t 60 -c copy "$OUTPUT_DIR/segment_19_1080-1140s.mp4"

echo "Extracting segment 20..."
ffmpeg -ss 1140 -i "$INPUT" -t 17.5 -c copy "$OUTPUT_DIR/segment_20_1140-1158s.mp4"
