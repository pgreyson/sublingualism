#!/usr/bin/env python3
"""Upload looped segment exports to Vimeo and map old->new Vimeo IDs."""

import os
import json
import requests
import sys

TOKEN = os.environ.get("VIMEO_ACCESS_TOKEN", "f91a90f3c8886a8c2f8eb2eb8a2f6b51")
HEADERS = {"Authorization": f"bearer {TOKEN}"}
LOOPED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports_looped")
RESULTS_FILE = os.path.join(LOOPED_DIR, "loop_results.json")
FOLDER_NAME = "2026-02-12 looped segments"


def create_folder():
    resp = requests.post(
        "https://api.vimeo.com/me/projects",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"name": FOLDER_NAME}
    )
    data = resp.json()
    if "uri" in data:
        print(f"Created folder: {data['uri']}")
        return data["uri"]
    # Folder might already exist
    resp2 = requests.get(
        "https://api.vimeo.com/me/projects",
        headers=HEADERS,
        params={"per_page": 50}
    )
    for proj in resp2.json().get("data", []):
        if proj["name"] == FOLDER_NAME:
            print(f"Found existing folder: {proj['uri']}")
            return proj["uri"]
    raise Exception(f"Failed to create folder: {data}")


def upload_video(filepath):
    """Upload a video using Vimeo's tus upload approach."""
    filesize = os.path.getsize(filepath)
    name = os.path.splitext(os.path.basename(filepath))[0]

    resp = requests.post(
        "https://api.vimeo.com/me/videos",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={
            "upload": {
                "approach": "tus",
                "size": str(filesize)
            },
            "name": name,
            "privacy": {"view": "anybody", "embed": "public"}
        }
    )
    data = resp.json()
    if "uri" not in data:
        print(f"\n  ERROR creating video: {data.get('error', data)}")
        return None

    video_uri = data["uri"]
    upload_link = data["upload"]["upload_link"]

    CHUNK_SIZE = 50 * 1024 * 1024  # 50MB chunks
    MAX_RETRIES = 3
    offset = 0
    with open(filepath, "rb") as f:
        while offset < filesize:
            f.seek(offset)
            chunk = f.read(CHUNK_SIZE)
            for attempt in range(MAX_RETRIES):
                try:
                    tus_resp = requests.patch(
                        upload_link,
                        headers={
                            "Tus-Resumable": "1.0.0",
                            "Upload-Offset": str(offset),
                            "Content-Type": "application/offset+octet-stream"
                        },
                        data=chunk,
                        timeout=120
                    )
                    if tus_resp.status_code not in (200, 204):
                        print(f"\n  ERROR uploading chunk at offset {offset}: {tus_resp.status_code}")
                        if attempt < MAX_RETRIES - 1:
                            import time; time.sleep(2)
                            continue
                        return None
                    offset = int(tus_resp.headers.get("Upload-Offset", offset + len(chunk)))
                    break
                except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
                    if attempt < MAX_RETRIES - 1:
                        print(f"\n  Retry {attempt+1}/{MAX_RETRIES} after error...")
                        import time; time.sleep(3)
                    else:
                        print(f"\n  FAILED after {MAX_RETRIES} retries: {e}")
                        return None
            pct = offset * 100 // filesize
            print(f"\r  Uploading... {pct}%", end="", flush=True)

    print()
    return video_uri


def add_to_folder(folder_uri, video_uri):
    video_id = video_uri.split("/")[-1]
    resp = requests.put(
        f"https://api.vimeo.com{folder_uri}/videos/{video_id}",
        headers=HEADERS
    )
    return resp.status_code in (200, 204)


def main():
    with open(RESULTS_FILE) as f:
        results = json.load(f)

    print(f"Uploading {len(results)} looped clips to Vimeo...")

    folder_uri = create_folder()
    print(f"Using folder: {folder_uri}\n")

    # Load existing mapping to support resume
    mapping_file = os.path.join(LOOPED_DIR, "vimeo_mapping.json")
    if os.path.exists(mapping_file):
        with open(mapping_file) as mf:
            mapping = json.load(mf)
        done_ids = {m["old_vimeo_id"] for m in mapping}
        print(f"Resuming: {len(done_ids)} already uploaded\n")
    else:
        mapping = []
        done_ids = set()

    for i, clip in enumerate(results, 1):
        filename = clip["output_file"]
        # Use mp4 version for upload (much smaller, Vimeo re-encodes anyway)
        mp4_name = filename.replace(".mov", ".mp4")
        mp4_path = os.path.join(LOOPED_DIR, "mp4", mp4_name)
        filepath = mp4_path if os.path.exists(mp4_path) else os.path.join(LOOPED_DIR, filename)
        old_vimeo_id = clip["vimeo_id"]
        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        print(f"[{i}/{len(results)}] {filename} ({size_mb:.0f}MB, replaces Vimeo {old_vimeo_id})")

        if old_vimeo_id in done_ids:
            print(f"  Already uploaded, skipping\n")
            continue

        video_uri = upload_video(filepath)
        if video_uri:
            new_vimeo_id = video_uri.split("/")[-1]
            add_to_folder(folder_uri, video_uri)
            mapping.append({
                "old_vimeo_id": old_vimeo_id,
                "new_vimeo_id": new_vimeo_id,
                "new_uri": video_uri,
                "file": filename,
                "loop_score": clip["loop_score"],
                "loop_duration": clip["loop_duration"]
            })
            print(f"  OK → Vimeo {new_vimeo_id}")
            # Save after each upload for resume support
            with open(mapping_file, "w") as mf:
                json.dump(mapping, mf, indent=2)
        else:
            print(f"  FAILED")
        print()

    # Save final mapping
    with open(mapping_file, "w") as f:
        json.dump(mapping, f, indent=2)

    print(f"\nDone: {len(mapping)}/{len(results)} uploaded")
    print(f"Mapping saved to {mapping_file}")
    print("\nMapping (old → new):")
    for m in mapping:
        print(f"  {m['old_vimeo_id']} → {m['new_vimeo_id']}")


if __name__ == "__main__":
    main()
