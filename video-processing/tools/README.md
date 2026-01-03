# Video Segmentation Tools

## Overview
Tools for automated video segmentation, EDL generation, and playlist creation.

## Tools

### 1. check_vimeo_downloads.py
Checks if Vimeo has generated download links for your videos.
```bash
python check_vimeo_downloads.py          # Quick check
python check_vimeo_downloads.py monitor  # Continuous monitoring
```

### 2. monitor_all_videos.py
Monitors all videos in your Vimeo account for download availability.
```bash
python monitor_all_videos.py
```

### 3. local_video_segmenter.py
Segments downloaded videos using scene detection or fixed intervals.
```bash
python local_video_segmenter.py video.mp4 scene 0.3    # Scene detection
python local_video_segmenter.py video.mp4 interval 30  # 30-second intervals
```

### 4. generate_edl.py
Core EDL generation functions used by other tools.

### 5. Other utilities
- `create_vlc_playlists.py` - Generates VLC-compatible playlists
- `video_scene_detector.py` - Advanced scene detection (when downloads work)
- `advanced_scene_detection.py` - Multi-method scene analysis

## Workflow

1. **Monitor downloads**: Run `monitor_all_videos.py` to check when videos are ready
2. **Download videos**: Once ready, download from Vimeo website or use API
3. **Segment videos**: Use `local_video_segmenter.py` on downloaded files
4. **Use outputs**:
   - EDL files → Import to video editing software
   - VLC playlists → Play segments in VLC
   - JSON files → Programmatic access to segment data
   - Extract scripts → Create individual clips

## Output Locations
- `/edl_files/` - Edit Decision Lists for video editors
- `/vlc_playlists/` - M3U and XSPF playlists
- `/json_data/` - Segment data in JSON format
- `/segments_*/` - Per-video output directories with all files