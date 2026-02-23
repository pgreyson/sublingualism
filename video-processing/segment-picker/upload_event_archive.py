#!/usr/bin/env python3
"""Upload event archive segments (video + posters) to S3.

Usage:
    python upload_event_archive.py <event-slug> <video-dir> <poster-dir>

Example:
    python upload_event_archive.py byob-gray-area /tmp/byob_segments/video_web /tmp/byob_segments/posters

Uploads to:
    s3://sublingualism-video/video/events/<event-slug>/
    s3://sublingualism-video/posters/events/<event-slug>/
"""

import os
import sys
import subprocess

def upload_dir(local_dir, s3_prefix, content_type):
    """Upload all files in local_dir to s3_prefix."""
    files = sorted(f for f in os.listdir(local_dir) if not f.startswith('.'))
    total = len(files)
    uploaded = 0
    skipped = 0

    for i, fname in enumerate(files):
        local_path = os.path.join(local_dir, fname)
        s3_path = f"{s3_prefix}{fname}"

        # Check if already uploaded
        result = subprocess.run(
            ['aws', 's3api', 'head-object', '--bucket', 'sublingualism-video', '--key', s3_path.replace('s3://sublingualism-video/', '')],
            capture_output=True
        )
        if result.returncode == 0:
            skipped += 1
            continue

        subprocess.run([
            'aws', 's3', 'cp', local_path, s3_path,
            '--content-type', content_type,
        ], capture_output=True, check=True)
        uploaded += 1

        if (i + 1) % 10 == 0 or i == total - 1:
            print(f"  {i+1}/{total} ({uploaded} uploaded, {skipped} skipped)", flush=True)

    return uploaded, skipped


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    event_slug = sys.argv[1]
    video_dir = sys.argv[2]
    poster_dir = sys.argv[3]

    print(f"Uploading event archive: {event_slug}")

    print(f"\nUploading videos from {video_dir}...")
    v_up, v_skip = upload_dir(video_dir, f"s3://sublingualism-video/video/events/{event_slug}/", "video/mp4")
    print(f"  Videos: {v_up} uploaded, {v_skip} skipped")

    print(f"\nUploading posters from {poster_dir}...")
    p_up, p_skip = upload_dir(poster_dir, f"s3://sublingualism-video/posters/events/{event_slug}/", "image/jpeg")
    print(f"  Posters: {p_up} uploaded, {p_skip} skipped")

    print(f"\nDone! CDN base: https://d2xbllb3qhv8ay.cloudfront.net/video/events/{event_slug}/")


if __name__ == "__main__":
    main()
