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

---

## Loop Finder Pipeline

`/segment-picker/` contains a pipeline for automatically finding seamless loop points in OBS recordings and uploading the best ones to Vimeo. The source material is 3840x1080 SBS ProRes captured from an Erogenous Tones Structure Eurorack video module.

### How it works

#### 1. Frame extraction (`scan_all_loops.py`)

For each recording, ffmpeg extracts frames at reduced resolution (240x68) and low framerate (3fps) and pipes them as raw RGB into numpy. This keeps memory bounded — full-res frames would be enormous. Extraction is chunked (30s windows with overlap) so large files don't blow up RAM.

#### 2. Sliding window loop detection

A window slides across each recording trying every possible clip length between 6–14 seconds, stepping 5 seconds forward each iteration. For each window position:

- The **first frame** is compared to the **last frame** using mean absolute pixel difference (int16 to avoid uint8 overflow wrapping)
- The difference is normalized to 0–1. Below a threshold of **0.06** = candidate loop point
- Lower score = more seamless loop. 0.0 would mean identical frames

This works well because the Structure module produces slowly-evolving generative video where the visual state often returns to something close to where it started within a ~10 second window.

#### 3. Visual interest scoring

To avoid selecting boring static segments, each candidate also gets a **visual interest** score — the standard deviation of pixel values across all frames in the segment. More movement and color variation = higher interest.

Black frames are detected and skipped (mean pixel value < 10).

#### 4. Selection (`select_and_upload.py`)

From hundreds of raw candidates (~487 across 14 recordings), overlapping segments are de-duped (minimum 15s separation). The survivors are ranked by a combined metric:

- **40% loop quality** (lower frame difference = better)
- **60% visual interest** (higher variance = better)

Capped at 8 segments per recording for diversity.

#### 5. Export and upload

ffmpeg cuts each selected segment from the original ProRes source and exports as mp4. Uploads to Vimeo use the tus resumable upload protocol via curl (Python requests had SSL issues with Vimeo's upload servers).

### Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `MIN_DURATION` | 6.0s | Shortest allowed loop |
| `MAX_DURATION` | 14.0s | Longest allowed loop |
| `STEP` | 5.0s | Window slide increment |
| `SAMPLE_FPS` | 3 | Frames per second for analysis |
| `SCORE_THRESHOLD` | 0.06 | Max first/last frame difference (0–1) |
| `MIN_SEPARATION` | 15.0s | Min gap between candidates to avoid overlap |
| `SCALE` | 240x68 | Analysis resolution (aspect-preserving from 3840x1080) |
| `CHUNK_SECS` | 30.0s | Extraction chunk size for memory management |

### Key files

- `scan_all_loops.py` — Scans all OBS recordings, outputs `candidates_cache.json` and `scan_results.json`
- `select_and_upload.py` — Ranks candidates, exports mp4s, uploads to Vimeo
- `find_loop_points.py` — Earlier single-file version of the loop finder
- `exports_all_loops/` — Scan results, upload mappings, exported mp4s
- `exports_looped/` — Original 12 hand-selected loops and their Vimeo mappings