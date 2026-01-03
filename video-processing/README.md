# Video Processing Tools

Tools for automated video segmentation and analysis for the Sublingualism project.

## Directory Structure

- `/tools/` - Python scripts for video processing
  - `local_video_segmenter.py` - Scene detection and interval-based segmentation
  - `check_vimeo_downloads.py` - Monitor Vimeo download availability
  - `frame_embedding_segmenter.py` - Advanced embedding-based segmentation
  - Additional utilities for EDL generation and playlist creation

- `/edl_files/` - Edit Decision Lists for video editing software
- `/vlc_playlists/` - VLC-compatible playlist files (.m3u, .xspf)
- `/json_data/` - Segment data in JSON format
- `/segments_*/` - Output directories for individual video processing

## Usage

### Basic Segmentation
```bash
python tools/local_video_segmenter.py /path/to/video.mp4 scene 0.3
```

### Check Vimeo Downloads
```bash
python tools/check_vimeo_downloads.py monitor
```

## Output Formats

- **EDL**: Industry-standard format for Premiere, Final Cut, DaVinci Resolve
- **VLC Playlists**: Play segments directly without re-encoding
- **JSON**: Programmatic access to segment data
- **Extract Scripts**: Shell scripts to create individual segment files