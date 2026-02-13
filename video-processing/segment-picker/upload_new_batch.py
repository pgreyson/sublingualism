#!/usr/bin/env python3
"""Select top N new loops, upload to Vimeo, save mapping."""

import json
import os
import subprocess
import time
from pathlib import Path

TOKEN = os.environ.get("VIMEO_ACCESS_TOKEN", "f91a90f3c8886a8c2f8eb2eb8a2f6b51")
MP4_DIR = Path(__file__).parent / "exports_all_loops" / "mp4"
CACHE = Path(__file__).parent / "exports_all_loops" / "candidates_cache.json"
EXISTING_RESULTS = Path(__file__).parent / "exports_looped" / "loop_results.json"
MAPPING_FILE = Path(__file__).parent / "exports_all_loops" / "vimeo_mapping.json"

TOP_N = 40
MIN_SEPARATION = 15.0

import requests
HEADERS = {"Authorization": f"bearer {TOKEN}"}


def select_top_n(n):
    with open(CACHE) as f:
        candidates = json.load(f)

    existing = set()
    with open(EXISTING_RESULTS) as f:
        for r in json.load(f):
            existing.add((r["video_id"], round(r["loop_start"])))

    by_video = {}
    for c in candidates:
        by_video.setdefault(c["video_id"], []).append(c)

    selected = []
    for vid, cands in by_video.items():
        cands.sort(key=lambda c: (c["loop_score"], -c["visual_interest"]))
        picked = []
        for c in cands:
            overlaps = any(abs(c["loop_start"] - p["loop_start"]) < MIN_SEPARATION for p in picked)
            if not overlaps:
                is_existing = any(c["video_id"] == ev and abs(c["loop_start"] - es) < MIN_SEPARATION for (ev, es) in existing)
                if not is_existing:
                    picked.append(c)
        selected.extend(picked)

    selected.sort(key=lambda c: c["loop_score"])
    return selected[:n]


def main():
    # Load existing uploads
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE) as f:
            mapping = json.load(f)
        done = {m["mp4_file"] for m in mapping}
    else:
        mapping = []
        done = set()

    segments = select_top_n(TOP_N)
    print(f"Selected {len(segments)} segments, {len(done)} already uploaded\n")

    for i, seg in enumerate(segments):
        vid = seg["video_id"]
        mp4_name = f"{vid}_t{int(seg['loop_start']):04d}_loop.mp4"
        mp4_path = MP4_DIR / mp4_name

        if mp4_name in done:
            print(f"[{i+1}/{len(segments)}] {mp4_name} — already uploaded")
            continue

        if not mp4_path.exists():
            print(f"[{i+1}/{len(segments)}] {mp4_name} — mp4 missing, skipping")
            continue

        filesize = mp4_path.stat().st_size
        name = mp4_name.replace(".mp4", "")
        print(f"[{i+1}/{len(segments)}] {mp4_name} ({filesize // (1024*1024)}MB, score={seg['loop_score']:.4f})")

        # Create video entry
        resp = requests.post(
            "https://api.vimeo.com/me/videos",
            headers={**HEADERS, "Content-Type": "application/json"},
            json={
                "upload": {"approach": "tus", "size": str(filesize)},
                "name": name,
                "privacy": {"view": "anybody", "embed": "public"}
            }
        )
        data = resp.json()
        if "uri" not in data:
            print(f"  ERROR: {data.get('error', data)}")
            continue

        video_uri = data["uri"]
        upload_link = data["upload"]["upload_link"]
        new_id = video_uri.split("/")[-1]

        # Upload via curl
        result = subprocess.run([
            "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
            "--retry", "3", "--retry-delay", "5",
            "-X", "PATCH", upload_link,
            "-H", "Tus-Resumable: 1.0.0",
            "-H", "Upload-Offset: 0",
            "-H", "Content-Type: application/offset+octet-stream",
            "--data-binary", f"@{mp4_path}",
            "--max-time", "300"
        ], capture_output=True, text=True)

        http_code = result.stdout.strip()
        if http_code not in ("200", "204"):
            print(f"  Upload failed (HTTP {http_code})")
            continue

        print(f"  → Vimeo {new_id}")

        mapping.append({
            "vimeo_id": new_id,
            "vimeo_uri": video_uri,
            "mp4_file": mp4_name,
            "video_id": vid,
            "loop_start": seg["loop_start"],
            "loop_duration": seg["loop_duration"],
            "loop_score": seg["loop_score"],
        })

        with open(MAPPING_FILE, "w") as f:
            json.dump(mapping, f, indent=2)

    print(f"\nDone! {len(mapping)} total uploaded")
    print(f"Mapping saved to {MAPPING_FILE}")


if __name__ == "__main__":
    main()
