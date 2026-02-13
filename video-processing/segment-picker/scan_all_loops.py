#!/usr/bin/env python3
"""
Scan ALL OBS recordings for good ~10s loop candidates.

Uses chunked frame extraction to keep memory bounded.
"""

import json
import subprocess
import numpy as np
import gc
import os
from pathlib import Path

OBS_DIR = "/Volumes/Workspace/obs_recordings"
OUT_DIR = Path(__file__).parent / "exports_all_loops"
EXISTING_RESULTS = Path(__file__).parent / "exports_looped" / "loop_results.json"

# Parameters
MIN_DURATION = 6.0
MAX_DURATION = 14.0
STEP = 5.0
SAMPLE_FPS = 3
SCORE_THRESHOLD = 0.06
MIN_SEPARATION = 15.0
SCALE_W, SCALE_H = 240, 68
CHUNK_SECS = 30.0  # extract this many seconds at a time


def get_video_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def extract_frames(video_path, start=0, duration=None, fps=SAMPLE_FPS):
    """Extract frames from a time range."""
    cmd = ["ffmpeg", "-v", "quiet", "-ss", str(start), "-i", video_path]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += [
        "-vf", f"fps={fps},scale={SCALE_W}:{SCALE_H}",
        "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"
    ]
    result = subprocess.run(cmd, capture_output=True)
    raw = result.stdout
    frame_size = SCALE_W * SCALE_H * 3
    n_frames = len(raw) // frame_size
    if n_frames == 0:
        return np.array([])
    frames = np.frombuffer(raw[:n_frames * frame_size], dtype=np.uint8)
    return frames.reshape(n_frames, SCALE_H, SCALE_W, 3)


def is_black_frame(frame, threshold=10):
    return np.mean(frame) < threshold


def frame_variance(frame):
    return np.std(frame.astype(float))


def scan_recording(mov_path):
    """Scan a recording for loop candidates using chunked extraction."""
    video_id = Path(mov_path).stem.replace(" ", "_")
    duration = get_video_duration(mov_path)

    if duration < MIN_DURATION + 2:
        print(f"  Skipping {video_id} ({duration:.0f}s) - too short")
        return video_id, []

    print(f"  Scanning {video_id} ({duration:.0f}s)...", flush=True)

    min_span = int(MIN_DURATION * SAMPLE_FPS)
    max_span = int(MAX_DURATION * SAMPLE_FPS)
    step_frames = int(STEP * SAMPLE_FPS)
    overlap = MAX_DURATION + 2  # seconds of overlap between chunks

    candidates = []
    chunk_start = 0.0

    while chunk_start < duration:
        chunk_dur = min(CHUNK_SECS + overlap, duration - chunk_start)
        if chunk_dur < MIN_DURATION:
            break

        frames = extract_frames(mov_path, start=chunk_start, duration=chunk_dur)
        n = len(frames)
        if n < min_span:
            chunk_start += CHUNK_SECS
            continue

        flat = frames.reshape(n, -1)

        # Only scan start points within the non-overlap region
        scan_limit = min(int(CHUNK_SECS * SAMPLE_FPS), n - min_span)

        sf = 0
        while sf < scan_limit and sf + min_span <= n:
            mid_f = min(sf + min_span // 2, n - 1)
            if is_black_frame(frames[mid_f]):
                sf += step_frames
                continue

            el = sf + min_span
            eh = min(sf + max_span + 1, n)
            if el >= eh:
                sf += step_frames
                continue

            start_flat = flat[sf].astype(np.int16)
            end_block = flat[el:eh].astype(np.int16)
            d = np.mean(np.abs(end_block - start_flat), axis=1) / 255.0
            bi = np.argmin(d)
            best_score = float(d[bi])
            best_end = el + int(bi)

            abs_start = chunk_start + sf / SAMPLE_FPS
            abs_end = chunk_start + best_end / SAMPLE_FPS

            mid = frames[(sf + best_end) // 2]
            interest = frame_variance(mid)

            candidates.append({
                "video_id": video_id,
                "loop_start": round(abs_start, 2),
                "loop_end": round(abs_end, 2),
                "loop_duration": round(abs_end - abs_start, 2),
                "loop_score": round(best_score, 6),
                "visual_interest": round(float(interest), 2),
                "source_path": mov_path,
            })

            sf += step_frames

        del frames, flat
        gc.collect()
        chunk_start += CHUNK_SECS

    print(f"    → {len(candidates)} candidates", flush=True)
    return video_id, candidates


def select_best_non_overlapping(candidates):
    by_video = {}
    for c in candidates:
        by_video.setdefault(c["video_id"], []).append(c)

    selected = []
    for vid, cands in by_video.items():
        cands.sort(key=lambda c: (c["loop_score"], -c["visual_interest"]))
        picked = []
        for c in cands:
            overlaps = any(
                abs(c["loop_start"] - p["loop_start"]) < MIN_SEPARATION
                for p in picked
            )
            if not overlaps:
                picked.append(c)
        selected.extend(picked)

    selected.sort(key=lambda c: c["loop_score"])
    return selected


def export_mp4(source_path, start_time, duration, output_path):
    subprocess.run([
        "ffmpeg", "-y", "-v", "quiet",
        "-ss", str(start_time), "-t", str(duration),
        "-i", source_path,
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-pix_fmt", "yuv420p", "-an",
        output_path
    ], check=True)


def main():
    OUT_DIR.mkdir(exist_ok=True)

    existing_segments = set()
    if EXISTING_RESULTS.exists():
        with open(EXISTING_RESULTS) as f:
            for r in json.load(f):
                existing_segments.add((r["video_id"], round(r["loop_start"])))

    recordings = sorted(Path(OBS_DIR).glob("*.mov"))
    print(f"Found {len(recordings)} recordings")
    print(f"Already have {len(existing_segments)} segments\n")

    # Load cached candidates from previous runs
    candidates_cache = OUT_DIR / "candidates_cache.json"
    all_candidates = []
    scanned_ids = set()
    if candidates_cache.exists():
        with open(candidates_cache) as f:
            all_candidates = json.load(f)
        scanned_ids = {c["video_id"] for c in all_candidates}
        print(f"Loaded {len(all_candidates)} cached candidates from {len(scanned_ids)} recordings\n")

    for mov in recordings:
        vid_id = mov.stem.replace(" ", "_")
        if vid_id in scanned_ids:
            print(f"  {vid_id}: cached, skipping")
            continue
        _, candidates = scan_recording(str(mov))
        good = [c for c in candidates if c["loop_score"] <= SCORE_THRESHOLD]
        all_candidates.extend(good)
        print(f"    → {len(good)} good of {len(candidates)} (score ≤ {SCORE_THRESHOLD})\n")
        gc.collect()
        # Save progress after each recording
        with open(candidates_cache, "w") as f:
            json.dump(all_candidates, f, indent=2)

    print(f"Total good candidates: {len(all_candidates)}")

    selected = select_best_non_overlapping(all_candidates)
    print(f"After de-overlap: {len(selected)}")

    new_segments = []
    for s in selected:
        is_existing = any(
            s["video_id"] == ev and abs(s["loop_start"] - es) < MIN_SEPARATION
            for (ev, es) in existing_segments
        )
        if not is_existing:
            new_segments.append(s)

    print(f"New segments (excluding existing): {len(new_segments)}\n")

    mp4_dir = OUT_DIR / "mp4"
    mp4_dir.mkdir(exist_ok=True)

    exported = []
    for i, seg in enumerate(new_segments):
        vid = seg["video_id"]
        seg_name = f"{vid}_t{int(seg['loop_start']):04d}_loop"
        mp4_path = str(mp4_dir / f"{seg_name}.mp4")

        print(f"[{i+1}/{len(new_segments)}] {seg_name} ({seg['loop_duration']:.1f}s, score={seg['loop_score']:.4f}, interest={seg['visual_interest']:.0f})")

        export_mp4(seg["source_path"], seg["loop_start"], seg["loop_duration"], mp4_path)
        file_size = os.path.getsize(mp4_path) / (1024 * 1024)
        print(f"  → {file_size:.1f}MB")

        seg["output_file"] = f"{seg_name}.mp4"
        seg["file_size_mb"] = round(file_size, 1)
        exported.append({k: v for k, v in seg.items() if k != "source_path"})

    results_path = OUT_DIR / "scan_results.json"
    with open(results_path, "w") as f:
        json.dump(exported, f, indent=2)

    print(f"\nDone! {len(exported)} new loops exported to {mp4_dir}")
    print(f"Results: {results_path}")


if __name__ == "__main__":
    main()
