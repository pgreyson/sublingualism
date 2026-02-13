#!/usr/bin/env python3
"""Upload top N new loop clips to Vimeo using curl for reliability."""

import json
import os
import requests
import subprocess
import time
from pathlib import Path

TOKEN = os.environ.get("VIMEO_ACCESS_TOKEN", "f91a90f3c8886a8c2f8eb2eb8a2f6b51")
HEADERS = {"Authorization": f"bearer {TOKEN}"}
SCAN_RESULTS = Path(__file__).parent / "exports_all_loops" / "scan_results.json"
MP4_DIR = Path(__file__).parent / "exports_all_loops" / "mp4"
UPLOAD_LOG = Path(__file__).parent / "exports_all_loops" / "vimeo_uploads.json"
FOLDER_URI = "/users/57827402/projects/28234454"

# How many to upload
TOP_N = 50
# Minimum visual interest to include
MIN_INTEREST = 10


def rank_clips(clips):
    """Rank by combined score: low loop_score (good match) + high visual_interest."""
    for c in clips:
        # Normalize: loop_score 0-0.06 → 0-1, interest 0-85 → 0-1
        score_norm = c["loop_score"] / 0.06
        interest_norm = c["visual_interest"] / 85.0
        # Combined: 60% loop quality, 40% visual interest
        c["rank_score"] = 0.6 * score_norm - 0.4 * interest_norm
    clips.sort(key=lambda c: c["rank_score"])
    return clips


def main():
    with open(SCAN_RESULTS) as f:
        clips = json.load(f)

    # Filter low-interest clips
    clips = [c for c in clips if c["visual_interest"] >= MIN_INTEREST]
    print(f"Loaded {len(clips)} clips (interest >= {MIN_INTEREST})")

    # Rank and pick top N
    clips = rank_clips(clips)
    batch = clips[:TOP_N]

    print(f"Uploading top {len(batch)} clips\n")

    # Load existing uploads
    if UPLOAD_LOG.exists():
        with open(UPLOAD_LOG) as f:
            uploads = json.load(f)
        done_files = {u["output_file"] for u in uploads}
    else:
        uploads = []
        done_files = set()

    batch = [c for c in batch if c["output_file"] not in done_files]
    print(f"Remaining to upload: {len(batch)}\n")

    for i, clip in enumerate(batch, 1):
        mp4_path = str(MP4_DIR / clip["output_file"])
        if not os.path.exists(mp4_path):
            print(f"  SKIP: {clip['output_file']} not found")
            continue

        filesize = os.path.getsize(mp4_path)
        size_mb = filesize / (1024 * 1024)
        name = clip["output_file"].replace(".mp4", "")

        print(f"[{i}/{len(batch)}] {name} ({size_mb:.0f}MB, score={clip['loop_score']:.4f}, interest={clip['visual_interest']:.0f})")

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
        new_vimeo_id = video_uri.split("/")[-1]

        # Upload via curl
        success = False
        for attempt in range(3):
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
            if http_code in ("200", "204"):
                success = True
                break
            else:
                print(f"  Retry {attempt+1} (HTTP {http_code})")
                time.sleep(5)

        if not success:
            print(f"  FAILED")
            continue

        # Add to folder
        requests.put(
            f"https://api.vimeo.com{FOLDER_URI}/videos/{new_vimeo_id}",
            headers=HEADERS
        )

        uploads.append({
            "output_file": clip["output_file"],
            "vimeo_id": new_vimeo_id,
            "vimeo_uri": video_uri,
            "loop_score": clip["loop_score"],
            "loop_duration": clip["loop_duration"],
            "visual_interest": clip["visual_interest"],
        })

        # Save after each upload
        with open(UPLOAD_LOG, "w") as f:
            json.dump(uploads, f, indent=2)

        print(f"  → Vimeo {new_vimeo_id}")

    # Get embed URLs for all uploaded videos
    print(f"\nDone! {len(uploads)} total uploaded")
    print(f"\nFetching embed URLs...")

    for u in uploads:
        if "embed_url" not in u:
            resp = requests.get(
                f"https://api.vimeo.com/videos/{u['vimeo_id']}",
                headers=HEADERS
            )
            d = resp.json()
            u["embed_url"] = d.get("player_embed_url", "")

    with open(UPLOAD_LOG, "w") as f:
        json.dump(uploads, f, indent=2)

    print("\nEmbed URLs:")
    for u in uploads:
        print(f"  {u['vimeo_id']}: {u.get('embed_url', 'N/A')}")


if __name__ == "__main__":
    main()
