#!/usr/bin/env python3
"""
Find optimal loop points for video segments.

For each clip in selected_12.json, goes back to the source OBS ProRes recording,
extracts frames around the clip's anchor point, and finds the best start/end
frame pair where first and last frames are visually similar — making a clean loop.

Outputs new ProRes clips to exports_looped/ directory.
"""

import json
import subprocess
import numpy as np
import sys
import os
from pathlib import Path

OBS_DIR = "/Volumes/Workspace/obs_recordings"
EXPORTS_DIR = Path(__file__).parent / "exports_looped"
SELECTED = Path(__file__).parent / "selected_12.json"

# Search window: how far before/after the original anchor to look
SEARCH_MARGIN = 5  # seconds before/after original start
MIN_DURATION = 4   # minimum clip length in seconds
MAX_DURATION = 14  # maximum clip length in seconds
SAMPLE_FPS = 5     # frames per second to sample for comparison (lower = faster)


def get_source_path(video_id):
    """Map video_id like '2026-02-07_19-39-37' back to OBS recording path."""
    # Convert underscore format back to space format
    name = video_id.replace("_", " ", 1).replace("_", " ", 1).replace("-", "-")
    # Try both .mov patterns
    for f in Path(OBS_DIR).glob("*.mov"):
        normalized = f.stem.replace(" ", "_").replace("_", "_")
        if video_id == normalized or video_id == f.stem.replace(" ", "_"):
            return str(f)
    # Direct name match
    candidate = Path(OBS_DIR) / f"{video_id.replace('_', ' ', 2)}.mov"
    if candidate.exists():
        return str(candidate)
    # Try replacing first two underscores with spaces
    parts = video_id.split("_")
    if len(parts) >= 3:
        candidate = Path(OBS_DIR) / f"{parts[0]} {parts[1]} {parts[2]}.mov"
        if candidate.exists():
            return str(candidate)
    # Fallback: match by date prefix
    date_part = video_id[:10]  # e.g. 2026-02-07
    time_part = video_id[11:]  # e.g. 19-39-37
    candidate = Path(OBS_DIR) / f"{date_part} {time_part}.mov"
    if candidate.exists():
        return str(candidate)
    return None


def get_video_duration(path):
    """Get video duration in seconds."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def extract_frames_as_array(video_path, start_time, duration, fps=SAMPLE_FPS):
    """Extract frames from video as numpy arrays using ffmpeg pipe."""
    # First get video dimensions
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0", video_path],
        capture_output=True, text=True
    )
    w, h = map(int, result.stdout.strip().split(","))

    # Scale down for faster comparison
    scale_w, scale_h = 480, 135  # roughly 1/8 of 3840x1080

    cmd = [
        "ffmpeg", "-v", "quiet",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", video_path,
        "-vf", f"fps={fps},scale={scale_w}:{scale_h}",
        "-pix_fmt", "rgb24",
        "-f", "rawvideo",
        "pipe:1"
    ]
    result = subprocess.run(cmd, capture_output=True)
    raw = result.stdout

    frame_size = scale_w * scale_h * 3
    n_frames = len(raw) // frame_size
    if n_frames == 0:
        return np.array([]), 0

    frames = np.frombuffer(raw[:n_frames * frame_size], dtype=np.uint8)
    frames = frames.reshape(n_frames, scale_h, scale_w, 3)
    return frames, n_frames


def frame_difference(frame_a, frame_b):
    """Mean absolute difference between two frames, normalized 0-1."""
    return np.mean(np.abs(frame_a.astype(float) - frame_b.astype(float))) / 255.0


def find_best_loop(frames, fps, min_dur, max_dur):
    """
    Find the best (start_frame, end_frame) pair where:
    - duration is between min_dur and max_dur
    - frame at start and frame at end are most similar
    Returns (start_idx, end_idx, score)
    """
    n = len(frames)
    min_frames = int(min_dur * fps)
    max_frames = min(int(max_dur * fps), n - 1)

    best_score = float('inf')
    best_start = 0
    best_end = n - 1

    # Try all valid start/end combinations
    # Start can be in the first quarter, end in the last quarter
    start_range = max(1, n // 4)
    end_range = max(1, n // 4)

    for start_idx in range(0, start_range):
        for end_idx in range(n - end_range, n):
            span = end_idx - start_idx
            if span < min_frames or span > max_frames:
                continue
            score = frame_difference(frames[start_idx], frames[end_idx])
            if score < best_score:
                best_score = score
                best_start = start_idx
                best_end = end_idx

    return best_start, best_end, best_score


def export_prores(source_path, start_time, duration, output_path):
    """Export a segment as ProRes 422."""
    cmd = [
        "ffmpeg", "-y", "-v", "quiet",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", source_path,
        "-c:v", "prores_ks",
        "-profile:v", "2",  # ProRes 422 Normal
        "-pix_fmt", "yuv422p10le",
        "-an",  # no audio
        output_path
    ]
    subprocess.run(cmd, check=True)


def main():
    with open(SELECTED) as f:
        clips = json.load(f)

    EXPORTS_DIR.mkdir(exist_ok=True)

    print(f"Processing {len(clips)} clips...")
    print(f"Search margin: ±{SEARCH_MARGIN}s, Duration range: {MIN_DURATION}-{MAX_DURATION}s")
    print(f"Output: {EXPORTS_DIR}")
    print()

    results = []

    for i, clip in enumerate(clips):
        video_id = clip["video_id"]
        orig_start = clip["start"]
        orig_duration = clip["duration"]
        vimeo_id = clip.get("vimeo_id", "unknown")
        seg_index = clip["seg_index"]

        print(f"[{i+1}/{len(clips)}] {video_id} seg{seg_index:03d} (Vimeo {vimeo_id})")
        print(f"  Original: start={orig_start}s, duration={orig_duration}s")

        source_path = get_source_path(video_id)
        if not source_path:
            print(f"  ERROR: Source recording not found for {video_id}")
            continue

        source_duration = get_video_duration(source_path)

        # Define search window
        search_start = max(0, orig_start - SEARCH_MARGIN)
        search_end = min(source_duration, orig_start + orig_duration + SEARCH_MARGIN)
        search_duration = search_end - search_start

        print(f"  Searching: {search_start:.1f}s - {search_end:.1f}s ({search_duration:.1f}s window)")

        # Extract frames for the search window
        frames, n_frames = extract_frames_as_array(
            source_path, search_start, search_duration, SAMPLE_FPS
        )

        if n_frames < SAMPLE_FPS * MIN_DURATION:
            print(f"  ERROR: Not enough frames ({n_frames})")
            continue

        # Find best loop points
        start_idx, end_idx, score = find_best_loop(
            frames, SAMPLE_FPS, MIN_DURATION, MAX_DURATION
        )

        # Convert frame indices back to absolute times
        loop_start = search_start + (start_idx / SAMPLE_FPS)
        loop_end = search_start + (end_idx / SAMPLE_FPS)
        loop_duration = loop_end - loop_start

        print(f"  Best loop: {loop_start:.2f}s - {loop_end:.2f}s ({loop_duration:.2f}s), score={score:.4f}")

        # Export as ProRes
        output_name = f"{video_id}_seg{seg_index:03d}_loop.mov"
        output_path = str(EXPORTS_DIR / output_name)
        export_prores(source_path, loop_start, loop_duration, output_path)

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  Exported: {output_name} ({file_size:.1f}MB)")
        print()

        results.append({
            "video_id": video_id,
            "seg_index": seg_index,
            "vimeo_id": vimeo_id,
            "original_start": orig_start,
            "original_duration": orig_duration,
            "loop_start": round(loop_start, 3),
            "loop_end": round(loop_end, 3),
            "loop_duration": round(loop_duration, 3),
            "loop_score": round(score, 6),
            "output_file": output_name
        })

    # Save results
    results_path = EXPORTS_DIR / "loop_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDone! {len(results)} clips exported to {EXPORTS_DIR}")
    print(f"Results saved to {results_path}")

    # Summary
    print("\nSummary:")
    for r in results:
        print(f"  {r['output_file']}: {r['loop_duration']:.1f}s (score={r['loop_score']:.4f})")


if __name__ == "__main__":
    main()
