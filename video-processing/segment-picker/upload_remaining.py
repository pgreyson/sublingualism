#!/usr/bin/env python3
"""Upload remaining looped clips to Vimeo using curl for the tus upload."""

import os
import json
import requests
import subprocess
import sys
import time

TOKEN = os.environ.get("VIMEO_ACCESS_TOKEN", "f91a90f3c8886a8c2f8eb2eb8a2f6b51")
HEADERS = {"Authorization": f"bearer {TOKEN}"}
LOOPED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports_looped")
RESULTS_FILE = os.path.join(LOOPED_DIR, "loop_results.json")
MAPPING_FILE = os.path.join(LOOPED_DIR, "vimeo_mapping.json")
FOLDER_URI = "/users/57827402/projects/28234454"


def main():
    with open(RESULTS_FILE) as f:
        results = json.load(f)

    # Load existing mapping
    if os.path.exists(MAPPING_FILE):
        with open(MAPPING_FILE) as mf:
            mapping = json.load(mf)
        done_ids = {m["old_vimeo_id"] for m in mapping}
    else:
        mapping = []
        done_ids = set()

    remaining = [c for c in results if c["vimeo_id"] not in done_ids]
    print(f"{len(done_ids)} already uploaded, {len(remaining)} remaining\n")

    for i, clip in enumerate(remaining, 1):
        filename = clip["output_file"]
        mp4_name = filename.replace(".mov", ".mp4")
        mp4_path = os.path.join(LOOPED_DIR, "mp4", mp4_name)
        filepath = mp4_path if os.path.exists(mp4_path) else os.path.join(LOOPED_DIR, filename)
        old_vimeo_id = clip["vimeo_id"]
        filesize = os.path.getsize(filepath)
        size_mb = filesize / (1024 * 1024)
        name = os.path.splitext(os.path.basename(filename))[0]

        print(f"[{i}/{len(remaining)}] {os.path.basename(filepath)} ({size_mb:.0f}MB, replaces Vimeo {old_vimeo_id})")

        # Step 1: Create video entry via API
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
            print(f"  ERROR creating video: {data.get('error', data)}")
            continue

        video_uri = data["uri"]
        upload_link = data["upload"]["upload_link"]
        new_vimeo_id = video_uri.split("/")[-1]
        print(f"  Created {video_uri}, uploading via curl...")

        # Step 2: Upload using curl (handles SSL better than Python requests)
        success = False
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

            http_code = result.stdout.strip()
            if http_code in ("200", "204"):
                print(f"  Upload OK (HTTP {http_code})")
                success = True
                break
            else:
                print(f"  Attempt {attempt+1} failed (HTTP {http_code}), retrying...")
                time.sleep(5)

        if not success:
            print(f"  FAILED after 3 attempts\n")
            continue

        # Step 3: Add to folder
        requests.put(
            f"https://api.vimeo.com{FOLDER_URI}/videos/{new_vimeo_id}",
            headers=HEADERS
        )

        mapping.append({
            "old_vimeo_id": old_vimeo_id,
            "new_vimeo_id": new_vimeo_id,
            "new_uri": video_uri,
            "file": filename,
            "loop_score": clip["loop_score"],
            "loop_duration": clip["loop_duration"]
        })
        print(f"  OK → Vimeo {new_vimeo_id}")

        # Save after each upload
        with open(MAPPING_FILE, "w") as mf:
            json.dump(mapping, mf, indent=2)
        print()

    print(f"\nDone: {len(mapping)}/{len(results)} uploaded")
    print(f"\nMapping (old → new):")
    for m in mapping:
        print(f"  {m['old_vimeo_id']} → {m['new_vimeo_id']}")


if __name__ == "__main__":
    main()
