#!/usr/bin/env python3
"""Generate thumbnails for every 10s segment of each video."""

import subprocess
import json
import os
import sys

VIDEO_DIR = "/Volumes/Workspace/obs_recordings"
THUMB_DIR = os.path.join(os.path.dirname(__file__), "thumbnails")
SEGMENT_DURATION = 10
THUMB_WIDTH = 480  # half of 960, keeps SBS readable

def get_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True
    )
    return float(json.loads(result.stdout)["format"]["duration"])

def generate_thumbnails(video_path, video_id):
    duration = get_duration(video_path)
    out_dir = os.path.join(THUMB_DIR, video_id)
    os.makedirs(out_dir, exist_ok=True)

    segments = []
    t = 0
    idx = 0
    while t < duration:
        end = min(t + SEGMENT_DURATION, duration)
        mid = (t + end) / 2
        thumb_path = os.path.join(out_dir, f"{idx:03d}.jpg")

        if not os.path.exists(thumb_path):
            subprocess.run([
                "ffmpeg", "-v", "quiet", "-ss", str(mid),
                "-i", video_path, "-frames:v", "1",
                "-vf", f"scale={THUMB_WIDTH}:-1",
                "-q:v", "4", thumb_path
            ])

        segments.append({
            "index": idx,
            "start": round(t, 2),
            "end": round(end, 2),
            "duration": round(end - t, 2),
            "thumbnail": f"thumbnails/{video_id}/{idx:03d}.jpg"
        })
        t += SEGMENT_DURATION
        idx += 1

    return {"video_id": video_id, "path": video_path, "duration": round(duration, 2), "segments": segments}

def main():
    videos = sorted(f for f in os.listdir(VIDEO_DIR) if f.endswith(".mov"))
    manifest = []

    for filename in videos:
        video_id = filename.replace(" ", "_").replace(".mov", "")
        video_path = os.path.join(VIDEO_DIR, filename)
        print(f"Processing {filename}...", flush=True)
        info = generate_thumbnails(video_path, video_id)
        manifest.append(info)
        print(f"  → {len(info['segments'])} segments", flush=True)

    manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\nManifest written to {manifest_path}")
    print(f"Total: {sum(len(v['segments']) for v in manifest)} segments across {len(manifest)} videos")

if __name__ == "__main__":
    main()
