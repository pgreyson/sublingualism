#!/usr/bin/env python3
"""Sort all clips by visual similarity and generate browse pages."""

import json
import os
import subprocess
import sys
import numpy as np
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "website")
POSTER_DIRS = ["/tmp/new_posters", "/tmp/existing_posters"]
CDN = "https://d2xbllb3qhv8ay.cloudfront.net"
CLIPS_PER_PAGE = 20


def get_poster_path(clip_id):
    """Find poster image for a clip, checking multiple locations."""
    for d in POSTER_DIRS:
        p = os.path.join(d, f"{clip_id}.jpg")
        if os.path.exists(p):
            return p
    return None


def extract_frame(clip_id):
    """Extract a frame from the video and crop to left eye."""
    mp4_path = os.path.join(BASE_DIR, "exports_all_loops", "mp4", f"{clip_id}_loop.mp4")
    if not os.path.exists(mp4_path):
        # Try without _loop suffix for Vimeo-era clips
        mp4_path = os.path.join(BASE_DIR, "exports_all_loops", "mp4", f"{clip_id}.mp4")
    if not os.path.exists(mp4_path):
        return None

    out = f"/tmp/frame_{clip_id}.jpg"
    if os.path.exists(out):
        return out
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp4_path, "-vf", "crop=iw/2:ih:0:0,scale=64:-1",
         "-frames:v", "1", "-q:v", "5", out],
        capture_output=True
    )
    return out if os.path.exists(out) else None


def image_features(path):
    """Extract color histogram + spatial features from an image."""
    img = Image.open(path).convert("RGB").resize((64, 36))
    arr = np.array(img, dtype=np.float32)

    # Color histogram features (per channel)
    hist_features = []
    for c in range(3):
        hist, _ = np.histogram(arr[:, :, c], bins=32, range=(0, 256))
        hist_features.extend(hist / hist.sum())

    # Spatial color layout (4x4 grid average colors)
    h, w = arr.shape[:2]
    spatial = []
    for gy in range(4):
        for gx in range(4):
            block = arr[gy*h//4:(gy+1)*h//4, gx*w//4:(gx+1)*w//4]
            spatial.extend(block.mean(axis=(0, 1)) / 255.0)

    features = np.array(hist_features + spatial, dtype=np.float32)
    norm = np.linalg.norm(features)
    if norm > 0:
        features /= norm
    return features


def greedy_nearest_neighbor(features_dict):
    """Sort clips using greedy nearest-neighbor traversal."""
    ids = list(features_dict.keys())
    if not ids:
        return []

    features = {k: v for k, v in features_dict.items() if v is not None}
    no_features = [k for k in ids if k not in features]

    if not features:
        return ids

    # Start with first clip
    remaining = set(features.keys())
    start = list(remaining)[0]
    order = [start]
    remaining.remove(start)

    while remaining:
        current = order[-1]
        best_sim = -1
        best_id = None
        for candidate in remaining:
            sim = float(np.dot(features[current], features[candidate]))
            if sim > best_sim:
                best_sim = sim
                best_id = candidate
        order.append(best_id)
        remaining.remove(best_id)
        if len(order) % 50 == 0:
            print(f"  Sorted {len(order)}/{len(features)} clips...")

    # Append clips with no features at end
    order.extend(no_features)
    return order


def generate_page_html(page_num, clips, total_pages):
    """Generate HTML for a browse page."""
    clips_html = "\n".join(
        f'            <div class="clip" data-id="{cid}">\n'
        f'                <video src="{CDN}/video/{cid}.mp4#t=0.001" preload="metadata" loop muted playsinline></video>\n'
        f'            </div>'
        for cid in clips
    )

    nav_parts = []
    for p in range(1, total_pages + 1):
        if p == page_num:
            nav_parts.append(f'<span class="current">{p}</span>')
        else:
            nav_parts.append(f'<a href="/clips-{p}.html">{p}</a>')
    page_nav = " ".join(nav_parts)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sublingualism</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #000;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .nav {{
            margin-bottom: 2rem;
            display: flex;
            gap: 1.5rem;
        }}
        .nav a {{
            color: #fff;
            text-decoration: none;
            opacity: 0.7;
        }}
        .nav a:hover {{
            opacity: 1;
        }}
        .clips-grid {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}
        .clip video {{
            width: 100%;
            display: block;
            background: #111;
            aspect-ratio: 32 / 9;
        }}
        .page-nav {{
            margin-top: 2rem;
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
        }}
        .page-nav a {{
            color: #fff;
            text-decoration: none;
            opacity: 0.5;
            font-size: 0.9rem;
        }}
        .page-nav a:hover {{
            opacity: 1;
        }}
        .page-nav .current {{
            opacity: 1;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/clips-all.html">&larr; all clips</a>
        </div>
        <div class="clips-grid">
{clips_html}
        </div>
        <div class="page-nav">
            {page_nav}
        </div>
    </div>
    <script src="/review.js"></script>
</body>
</html>
'''


def generate_index_html(pages, total_pages):
    """Generate clips-all.html with page cards."""
    cards = []
    for page_num, clips in enumerate(pages, 1):
        count = len(clips)
        # Sample 6 representative thumbnails
        indices = []
        if count <= 6:
            indices = list(range(count))
        else:
            step = count / 6
            indices = [int(i * step) for i in range(6)]

        thumbs = "\n".join(
            f'                    <img src="{CDN}/posters/{clips[i]}.jpg" alt="" loading="lazy">'
            for i in indices
        )

        cards.append(f'''            <a class="page-link" href="/clips-{page_num}.html">
                <div class="header">
                    <div class="label">page {page_num}</div>
                    <div class="count">{count} clips</div>
                </div>
                <div class="thumbs">
{thumbs}
                </div>
            </a>''')

    cards_html = "\n".join(cards)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sublingualism</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #000;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .nav {{
            margin-bottom: 2rem;
        }}
        .nav a {{
            color: #fff;
            text-decoration: none;
            opacity: 0.7;
        }}
        .nav a:hover {{
            opacity: 1;
        }}
        .page-links {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-top: 1rem;
        }}
        .page-link {{
            display: block;
            border: 1px solid rgba(255,255,255,0.2);
            padding: 1rem;
            text-decoration: none;
            color: #fff;
            transition: border-color 0.2s;
        }}
        .page-link:hover {{
            border-color: rgba(255,255,255,0.6);
        }}
        .page-link .header {{
            display: flex;
            align-items: baseline;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }}
        .page-link .label {{
            font-size: 1.1rem;
        }}
        .page-link .count {{
            opacity: 0.5;
            font-size: 0.85rem;
        }}
        .page-link .thumbs {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 2px;
        }}
        .page-link .thumbs img {{
            width: 100%;
            display: block;
            background: #111;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/clips.html">&larr; clips</a>
        </div>
        <h2 style="opacity:0.8; font-weight:normal; margin-bottom:1.5rem;">all clips</h2>
        <div class="page-links">
{cards_html}
        </div>
    </div>
</body>
</html>
'''


def main():
    # Collect all clip IDs: existing pages + new from scan
    existing_ids = []
    for page_num in range(1, 100):
        page_file = os.path.join(WEBSITE_DIR, f"clips-{page_num}.html")
        if not os.path.exists(page_file):
            break
        with open(page_file) as f:
            content = f.read()
        import re
        ids = re.findall(r'data-id="([^"]+)"', content)
        existing_ids.extend(ids)

    print(f"Found {len(existing_ids)} existing clips on pages")

    # Read new clips to add
    new_clips_file = "/tmp/new_clips_to_add.txt"
    new_ids = []
    if os.path.exists(new_clips_file):
        with open(new_clips_file) as f:
            new_ids = [line.strip() for line in f if line.strip()]

    print(f"Found {len(new_ids)} new clips to add")

    all_ids = list(dict.fromkeys(existing_ids + new_ids))  # dedupe preserving order
    print(f"Total unique clips: {len(all_ids)}")

    # For clips that use the _loop video naming, check both naming conventions
    # On S3, videos are stored as {id}.mp4 where id may or may not have _loop
    # Check which IDs need _loop suffix for their video URL

    # Compute features for similarity sorting
    print("\nComputing visual features...")
    features = {}
    for i, cid in enumerate(all_ids):
        poster = get_poster_path(cid)
        if poster:
            try:
                features[cid] = image_features(poster)
            except Exception as e:
                print(f"  Warning: failed to process poster for {cid}: {e}")
                features[cid] = None
        else:
            # Try extracting a frame
            frame = extract_frame(cid)
            if frame:
                try:
                    features[cid] = image_features(frame)
                except Exception:
                    features[cid] = None
            else:
                features[cid] = None

        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1}/{len(all_ids)} clips")

    valid = sum(1 for v in features.values() if v is not None)
    print(f"Got features for {valid}/{len(all_ids)} clips")

    # Sort by similarity
    print("\nSorting by visual similarity...")
    sorted_ids = greedy_nearest_neighbor(features)
    print(f"Sorted {len(sorted_ids)} clips")

    # Split into pages
    pages = []
    for i in range(0, len(sorted_ids), CLIPS_PER_PAGE):
        pages.append(sorted_ids[i:i + CLIPS_PER_PAGE])

    total_pages = len(pages)
    print(f"\nGenerating {total_pages} pages...")

    # Figure out which IDs need _loop suffix in their video URL
    # Check S3 existing file to determine naming
    s3_existing = set()
    s3_file = "/tmp/s3_existing.txt"
    if os.path.exists(s3_file):
        with open(s3_file) as f:
            for line in f:
                line = line.strip()
                if "→" in line:
                    line = line.split("→", 1)[1].strip()
                if line:
                    s3_existing.add(line)

    # Generate browse pages
    for page_num, clips in enumerate(pages, 1):
        html = generate_page_html(page_num, clips, total_pages)
        path = os.path.join(WEBSITE_DIR, f"clips-{page_num}.html")
        with open(path, "w") as f:
            f.write(html)
        print(f"  Generated clips-{page_num}.html ({len(clips)} clips)")

    # Remove extra old pages
    for old_page in range(total_pages + 1, 50):
        old_path = os.path.join(WEBSITE_DIR, f"clips-{old_page}.html")
        if os.path.exists(old_path):
            os.remove(old_path)
            print(f"  Removed old clips-{old_page}.html")
        else:
            break

    # Generate index page
    index_html = generate_index_html(pages, total_pages)
    index_path = os.path.join(WEBSITE_DIR, "clips-all.html")
    with open(index_path, "w") as f:
        f.write(index_html)
    print(f"  Generated clips-all.html")

    print(f"\nDone! {len(sorted_ids)} clips across {total_pages} pages")


if __name__ == "__main__":
    main()
