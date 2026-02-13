#!/usr/bin/env python3
"""Select best 30 new loops from scan results and upload to Vimeo."""

import json
import subprocess
import os
import time
from pathlib import Path

TOKEN = os.environ.get("VIMEO_ACCESS_TOKEN", "f91a90f3c8886a8c2f8eb2eb8a2f6b51")
HEADERS = {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"}
BASE_DIR = Path(__file__).parent
SCAN_RESULTS = BASE_DIR / "exports_all_loops" / "scan_results.json"
MP4_DIR = BASE_DIR / "exports_all_loops" / "mp4"
UPLOAD_MAPPING = BASE_DIR / "exports_all_loops" / "vimeo_upload_mapping.json"
FOLDER_URI = "/users/57827402/projects/28234454"

TARGET_COUNT = 30


def select_best(results, target=TARGET_COUNT):
    """Select best loops: low score, high interest, diverse recordings."""
    # Filter: score < 0.03 and interest > 30
    good = [s for s in results if s["loop_score"] < 0.03 and s["visual_interest"] > 30]
    # Sort by combined metric: lower is better
    # Normalize score (0-0.03) and interest (30-85) to 0-1, combine
    for s in good:
        norm_score = s["loop_score"] / 0.03  # 0=perfect, 1=threshold
        norm_interest = 1.0 - (s["visual_interest"] - 30) / 55.0  # 0=most interesting
        s["_rank"] = norm_score * 0.4 + norm_interest * 0.6  # weight interest more

    good.sort(key=lambda s: s["_rank"])

    # Ensure diversity: max 8 per recording
    selected = []
    per_vid = {}
    for s in good:
        vid = s["video_id"]
        per_vid.setdefault(vid, 0)
        if per_vid[vid] >= 8:
            continue
        per_vid[vid] += 1
        selected.append(s)
        if len(selected) >= target:
            break

    return selected


def upload_via_curl(filepath, name, token):
    """Create Vimeo entry and upload via curl."""
    import requests
    filesize = os.path.getsize(filepath)

    # Create video
    resp = requests.post(
        "https://api.vimeo.com/me/videos",
        headers=HEADERS,
        json={
            "upload": {"approach": "tus", "size": str(filesize)},
            "name": name,
            "privacy": {"view": "anybody", "embed": "public"}
        }
    )
    data = resp.json()
    if "uri" not in data:
        print(f"  ERROR creating video: {data.get('error', data)}")
        return None, None

    video_uri = data["uri"]
    upload_link = data["upload"]["upload_link"]
    new_id = video_uri.split("/")[-1]

    # Upload via curl
    for attempt in range(3):
        result = subprocess.run([
            "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
            "--retry", "3", "--retry-delay", "5",
            "-X", "PATCH", upload_link,
            "-H", "Tus-Resumable: 1.0.0",
            "-H", "Upload-Offset: 0",
            "-H", "Content-Type: application/offset+octet-stream",
            "--data-binary", f"@{filepath}",
            "--max-time", "300"
        ], capture_output=True, text=True)

        if result.stdout.strip() in ("200", "204"):
            # Add to folder
            import requests as req
            req.put(
                f"https://api.vimeo.com{FOLDER_URI}/videos/{new_id}",
                headers={"Authorization": f"bearer {token}"}
            )
            return new_id, video_uri
        time.sleep(5)

    return None, None


def main():
    with open(SCAN_RESULTS) as f:
        results = json.load(f)

    # Load existing uploads
    uploaded = []
    if UPLOAD_MAPPING.exists():
        with open(UPLOAD_MAPPING) as f:
            uploaded = json.load(f)
    done_files = {u["output_file"] for u in uploaded}

    selected = select_best(results)
    print(f"Selected {len(selected)} loops for upload\n")

    for i, seg in enumerate(selected):
        fname = seg["output_file"]
        if fname in done_files:
            print(f"[{i+1}/{len(selected)}] {fname} - already uploaded, skipping")
            continue

        filepath = str(MP4_DIR / fname)
        if not os.path.exists(filepath):
            print(f"[{i+1}/{len(selected)}] {fname} - FILE NOT FOUND, skipping")
            continue

        size_mb = os.path.getsize(filepath) / (1024*1024)
        name = fname.replace(".mp4", "")
        print(f"[{i+1}/{len(selected)}] {fname} ({size_mb:.1f}MB, score={seg['loop_score']:.4f}, interest={seg['visual_interest']:.0f})")

        new_id, uri = upload_via_curl(filepath, name, TOKEN)
        if new_id:
            print(f"  → Vimeo {new_id}")
            uploaded.append({
                "vimeo_id": new_id,
                "uri": uri,
                "output_file": fname,
                "video_id": seg["video_id"],
                "loop_start": seg["loop_start"],
                "loop_duration": seg["loop_duration"],
                "loop_score": seg["loop_score"],
                "visual_interest": seg["visual_interest"]
            })
            with open(UPLOAD_MAPPING, "w") as f:
                json.dump(uploaded, f, indent=2)
        else:
            print(f"  FAILED")

    print(f"\nDone! {len(uploaded)} total uploaded")
    print(f"Mapping saved to {UPLOAD_MAPPING}")


if __name__ == "__main__":
    main()
