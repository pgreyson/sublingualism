#!/usr/bin/env python3
"""Upload selected new loops to Vimeo using curl for reliable tus uploads."""

import os
import json
import requests
import subprocess
import time
from pathlib import Path

TOKEN = os.environ.get("VIMEO_ACCESS_TOKEN", "f91a90f3c8886a8c2f8eb2eb8a2f6b51")
HEADERS = {"Authorization": f"bearer {TOKEN}"}
BASE_DIR = Path(__file__).parent
SELECTED_FILE = BASE_DIR / "exports_all_loops" / "selected_new.json"
MP4_DIR = BASE_DIR / "exports_all_loops" / "mp4"
MAPPING_FILE = BASE_DIR / "exports_all_loops" / "new_vimeo_mapping.json"
FOLDER_URI = "/users/57827402/projects/28234454"


def main():
    with open(SELECTED_FILE) as f:
        selected = json.load(f)

    # Load existing mapping for resume
    mapping = []
    done_files = set()
    if MAPPING_FILE.exists():
        with open(MAPPING_FILE) as f:
            mapping = json.load(f)
        done_files = {m["file"] for m in mapping}

    remaining = [s for s in selected if f"{s['video_id']}_t{int(s['loop_start']):04d}_loop.mp4" not in done_files]
    print(f"{len(done_files)} already uploaded, {len(remaining)} remaining\n")

    for i, seg in enumerate(remaining, 1):
        fname = f"{seg['video_id']}_t{int(seg['loop_start']):04d}_loop.mp4"
        fpath = str(MP4_DIR / fname)
        if not os.path.exists(fpath):
            print(f"[{i}/{len(remaining)}] SKIP {fname} - not found")
            continue

        fsize = os.path.getsize(fpath)
        name = fname.replace(".mp4", "")

        print(f"[{i}/{len(remaining)}] {fname} ({fsize // (1024*1024)}MB)", end=" ", flush=True)

        # Create video entry
        resp = requests.post(
            "https://api.vimeo.com/me/videos",
            headers={**HEADERS, "Content-Type": "application/json"},
            json={
                "upload": {"approach": "tus", "size": str(fsize)},
                "name": name,
                "privacy": {"view": "anybody", "embed": "public"}
            }
        )
        data = resp.json()
        if "uri" not in data:
            print(f"ERROR: {data.get('error', data)}")
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
            "--data-binary", f"@{fpath}",
            "--max-time", "300"
        ], capture_output=True, text=True)

        http_code = result.stdout.strip()
        if http_code not in ("200", "204"):
            print(f"UPLOAD FAILED (HTTP {http_code})")
            continue

        # Add to folder
        requests.put(
            f"https://api.vimeo.com{FOLDER_URI}/videos/{new_id}",
            headers=HEADERS
        )

        mapping.append({
            "file": fname,
            "vimeo_id": new_id,
            "uri": video_uri,
            "loop_score": seg["loop_score"],
            "loop_duration": seg["loop_duration"],
            "visual_interest": seg["visual_interest"],
        })

        # Save after each
        with open(MAPPING_FILE, "w") as f:
            json.dump(mapping, f, indent=2)

        print(f"→ {new_id}")

    print(f"\nDone: {len(mapping)} uploaded")


if __name__ == "__main__":
    main()
