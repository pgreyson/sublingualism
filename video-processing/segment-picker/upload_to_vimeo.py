#!/usr/bin/env python3
"""Upload exported segments to Vimeo in a dated folder."""

import os
import json
import requests
import sys

TOKEN = os.environ.get("VIMEO_ACCESS_TOKEN", "f91a90f3c8886a8c2f8eb2eb8a2f6b51")
HEADERS = {"Authorization": f"bearer {TOKEN}"}
EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")
FOLDER_NAME = "2026-02-11 segments"


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
    elif "error" in data:
        # Folder might already exist, list and find it
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

    # Step 1: Create the video and get upload link
    resp = requests.post(
        "https://api.vimeo.com/me/videos",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={
            "upload": {
                "approach": "tus",
                "size": str(filesize)
            },
            "name": name,
            "privacy": {"view": "nobody", "embed": "private"}
        }
    )
    data = resp.json()
    if "uri" not in data:
        print(f"  ERROR creating video: {data.get('error', data)}")
        return None

    video_uri = data["uri"]
    upload_link = data["upload"]["upload_link"]

    # Step 2: Upload the file via tus in chunks
    CHUNK_SIZE = 2 * 1024 * 1024  # 2MB chunks
    offset = 0
    with open(filepath, "rb") as f:
        while offset < filesize:
            chunk = f.read(CHUNK_SIZE)
            tus_resp = requests.patch(
                upload_link,
                headers={
                    "Tus-Resumable": "1.0.0",
                    "Upload-Offset": str(offset),
                    "Content-Type": "application/offset+octet-stream"
                },
                data=chunk
            )
            if tus_resp.status_code not in (200, 204):
                print(f"  ERROR uploading chunk at offset {offset}: {tus_resp.status_code}")
                return None
            offset = int(tus_resp.headers.get("Upload-Offset", offset + len(chunk)))

    return video_uri


def add_to_folder(folder_uri, video_uri):
    """Add a video to a folder/project."""
    video_id = video_uri.split("/")[-1]
    resp = requests.put(
        f"https://api.vimeo.com{folder_uri}/videos/{video_id}",
        headers=HEADERS
    )
    return resp.status_code in (200, 204)


def main():
    files = sorted(f for f in os.listdir(EXPORT_DIR) if f.endswith(".mp4"))
    print(f"Found {len(files)} clips to upload")

    folder_uri = create_folder()
    print(f"Using folder: {folder_uri}\n")

    uploaded = []
    for i, filename in enumerate(files, 1):
        filepath = os.path.join(EXPORT_DIR, filename)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"[{i}/{len(files)}] {filename} ({size_mb:.1f}MB)...", end=" ", flush=True)

        video_uri = upload_video(filepath)
        if video_uri:
            add_to_folder(folder_uri, video_uri)
            uploaded.append({"file": filename, "uri": video_uri})
            print(f"OK → {video_uri}")
        else:
            print("FAILED")

    print(f"\nDone: {len(uploaded)}/{len(files)} uploaded to '{FOLDER_NAME}'")


if __name__ == "__main__":
    main()
