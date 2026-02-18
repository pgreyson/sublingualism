#!/usr/bin/env python3
"""
Analyze poster images and generate a recommendations page.
Uses diversified selection: picks the best clip, then penalizes similar clips
before picking the next, so the final set covers a range of visual styles.
"""

import os
import sys
import json
import re
import urllib.request
import numpy as np
from PIL import Image
from io import BytesIO

CDN = "https://d2xbllb3qhv8ay.cloudfront.net"


def load_curated_ids():
    """Parse curated clip IDs from clips.html."""
    website_dir = os.path.join(os.path.dirname(__file__), '..', 'website')
    path = os.path.join(website_dir, 'clips.html')
    with open(path) as f:
        content = f.read()
    return set(re.findall(r'data-id="([^"]+)"', content))


def load_all_clip_ids():
    """Parse clip IDs from the browse pages."""
    website_dir = os.path.join(os.path.dirname(__file__), '..', 'website')
    all_ids = []
    for i in range(1, 20):
        path = os.path.join(website_dir, f'clips-{i}.html')
        if not os.path.exists(path):
            continue
        with open(path) as f:
            content = f.read()
        for cid in re.findall(r'data-id="([^"]+)"', content):
            if cid not in all_ids:
                all_ids.append(cid)
    return all_ids


def download_poster(clip_id):
    """Download a poster image, return PIL Image or None."""
    url = f"{CDN}/posters/{clip_id}.jpg"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read()
        return Image.open(BytesIO(data)).convert('RGB')
    except Exception as e:
        print(f"  Failed to download {clip_id}: {e}")
        return None


def extract_features(img):
    """
    Extract a rich feature vector for an image.
    Returns a dict with scalar metrics and a feature vector for similarity.
    """
    img_resized = img.resize((384, 216), Image.LANCZOS)
    arr = np.array(img_resized, dtype=np.float32)
    h, w, _ = arr.shape

    # --- Scalar metrics for interest scoring ---

    # Color richness
    color_std = np.mean([arr[:, :, c].std() for c in range(3)])

    # Brightness
    brightness = arr.mean() / 255.0

    # Contrast
    gray = arr.mean(axis=2)
    p5, p95 = np.percentile(gray, 5), np.percentile(gray, 95)
    contrast = (p95 - p5) / 255.0

    # Saturation
    maxc = arr.max(axis=2)
    minc = arr.min(axis=2)
    delta = maxc - minc
    with np.errstate(divide='ignore', invalid='ignore'):
        sat_map = np.where(maxc > 0, delta / maxc, 0)
    saturation = sat_map.mean()

    # Spatial complexity via gradient magnitude
    gx = np.diff(gray, axis=1)
    gy = np.diff(gray, axis=0)
    mh = min(gx.shape[0], gy.shape[0])
    mw = min(gx.shape[1], gy.shape[1])
    grad_mag = np.sqrt(gx[:mh, :mw] ** 2 + gy[:mh, :mw] ** 2)
    complexity = grad_mag.mean() / 255.0

    # Color diversity (hue entropy)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    hue = np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)
    saturated_mask = sat_map > 0.1
    if saturated_mask.sum() > 100:
        hue_bins = np.histogram(hue[saturated_mask].flatten(), bins=12)[0]
        hue_norm = hue_bins / (hue_bins.sum() + 1e-8)
        color_diversity = -np.sum(hue_norm * np.log(hue_norm + 1e-8))
    else:
        color_diversity = 0.0

    # --- Feature vector for similarity comparison ---
    # Use a 4x4 grid of mean RGB values (48 dimensions)
    # Plus a color histogram (36 dimensions: 12 hue bins x 3 saturation levels)
    # Total: 84 dimensions

    # 4x4 spatial grid
    grid_h, grid_w = 4, 4
    grid_features = []
    for gy_i in range(grid_h):
        for gx_i in range(grid_w):
            y0 = gy_i * h // grid_h
            y1 = (gy_i + 1) * h // grid_h
            x0 = gx_i * w // grid_w
            x1 = (gx_i + 1) * w // grid_w
            cell = arr[y0:y1, x0:x1]
            grid_features.extend(cell.mean(axis=(0, 1)) / 255.0)

    # Color histogram: hue (12 bins) x saturation level (3 levels)
    color_hist = np.zeros(36)
    hue_flat = hue.flatten()
    sat_flat = sat_map.flatten()
    # Bin hue into 12 bins
    hue_binned = ((hue_flat + np.pi) / (2 * np.pi) * 12).astype(int).clip(0, 11)
    # Bin saturation into 3 levels: low (<0.2), mid (0.2-0.5), high (>0.5)
    sat_binned = np.where(sat_flat < 0.2, 0, np.where(sat_flat < 0.5, 1, 2))
    for hi in range(12):
        for si in range(3):
            mask = (hue_binned == hi) & (sat_binned == si)
            color_hist[hi * 3 + si] = mask.sum()
    color_hist = color_hist / (color_hist.sum() + 1e-8)

    feature_vec = np.array(grid_features + list(color_hist))

    return {
        'color_std': float(color_std),
        'brightness': float(brightness),
        'contrast': float(contrast),
        'saturation': float(saturation),
        'complexity': float(complexity),
        'color_diversity': float(color_diversity),
        'features': feature_vec,
    }


def interest_score(metrics):
    """Pure visual interest score (0-1ish)."""
    return (
        metrics['contrast'] * 0.20
        + metrics['saturation'] * 0.20
        + metrics['complexity'] * 0.15
        + metrics['color_diversity'] / 2.5 * 0.15
        + (1.0 - abs(metrics['brightness'] - 0.4) * 2) * 0.10
        + metrics['color_std'] / 80.0 * 0.20
    )


def diversified_select(candidates, curated_features, n=30):
    """
    Greedy diversified selection.

    1. Score all candidates by interest + taste similarity.
    2. Pick the top scorer.
    3. For remaining candidates, penalize those too similar to any already-selected clip.
    4. Repeat until we have n clips.

    This ensures visual variety in the final set.
    """
    # Compute base scores
    scored = []
    for cid, metrics in candidates:
        base = interest_score(metrics)

        # Taste similarity: distance to nearest curated clip
        if curated_features:
            dists = [np.linalg.norm(metrics['features'] - cf) for cf in curated_features]
            min_dist = min(dists)
            taste_sim = 1.0 / (1.0 + min_dist * 3)
        else:
            taste_sim = 0.5

        # 70% interest, 30% taste match
        score = base * 0.7 + taste_sim * 0.3
        scored.append({
            'id': cid,
            'metrics': metrics,
            'base_score': score,
            'effective_score': score,
            'interest': base,
            'taste_sim': taste_sim,
        })

    selected = []
    remaining = list(scored)

    for pick_num in range(min(n, len(remaining))):
        # Sort by effective score
        remaining.sort(key=lambda x: x['effective_score'], reverse=True)

        # Pick the top
        chosen = remaining.pop(0)
        selected.append(chosen)

        # Penalize remaining clips that are too similar to the chosen one
        chosen_feat = chosen['metrics']['features']
        for item in remaining:
            dist = np.linalg.norm(item['metrics']['features'] - chosen_feat)
            # Strong penalty for very similar clips (dist < 0.3),
            # tapering off for more distinct ones
            if dist < 0.8:
                penalty = (0.8 - dist) / 0.8 * 0.15  # up to 15% penalty per similar pick
                item['effective_score'] -= penalty

    return selected


def generate_page(selected_clips):
    """Generate recommendations.html matching curated page style."""
    parts = ['''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="preconnect" href="https://d2xbllb3qhv8ay.cloudfront.net">
    <title>Sublingualism — recommendations</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #000;
            color: #fff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem;
        }
        @media (min-width: 600px) {
            .container { padding: 2rem; }
        }
        .nav {
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .nav a {
            color: #fff;
            text-decoration: none;
            opacity: 0.7;
        }
        .nav a:hover {
            opacity: 1;
        }
        .clips-grid {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        @keyframes spin {
            to { transform: translate(-50%,-50%) rotate(360deg); }
        }
        .clip {
            cursor: pointer;
            position: relative;
            aspect-ratio: 16 / 9;
        }
        .clip::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 20px;
            height: 20px;
            border: 2px solid rgba(255,255,255,0.15);
            border-top-color: rgba(255,255,255,0.6);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            transform: translate(-50%,-50%);
        }
        .clip.loaded::before {
            display: none;
        }
        .clip img {
            width: 100%;
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            <a href="/clips.html">\u2190 curated</a>
        </div>
        <div class="clips-grid">
''']

    for item in selected_clips:
        cid = item['id']
        parts.append(
            f'            <div class="clip" data-id="{cid}" '
            f'data-src="{CDN}/video/{cid}.mp4#t=0.001">'
            f'<img src="{CDN}/posters/{cid}.jpg" alt="" '
            f'onload="this.parentNode.classList.add(\'loaded\')">'
            f'</div>\n'
        )

    parts.append('''        </div>
    </div>
    <script src="review.js"></script>
</body>
</html>
''')
    return ''.join(parts)


def main():
    curated_ids = load_curated_ids()
    all_ids = load_all_clip_ids()
    candidate_ids = [c for c in all_ids if c not in curated_ids]

    print(f"Total archive: {len(all_ids)}")
    print(f"Already curated: {len(curated_ids)}")
    print(f"Candidates: {len(candidate_ids)}")

    # Analyze curated clips for taste profile
    print("\nBuilding taste profile from curated clips...")
    curated_features = []
    for cid in curated_ids:
        img = download_poster(cid)
        if img:
            feat = extract_features(img)
            curated_features.append(feat['features'])
            sys.stdout.write('.')
            sys.stdout.flush()
    print(f"\nTaste profile from {len(curated_features)} clips")

    # Analyze all candidates
    print(f"\nAnalyzing {len(candidate_ids)} candidates...")
    candidates = []
    for i, cid in enumerate(candidate_ids):
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(candidate_ids)}...")
        img = download_poster(cid)
        if img is None:
            continue
        metrics = extract_features(img)
        candidates.append((cid, metrics))

    print(f"\nSuccessfully analyzed {len(candidates)} clips")

    # Diversified selection
    selected = diversified_select(candidates, curated_features, n=30)

    print(f"\nTop 30 diversified recommendations:")
    for i, item in enumerate(selected):
        print(f"  {i + 1:2d}. {item['id']:40s}  "
              f"score={item['effective_score']:.3f}  "
              f"interest={item['interest']:.3f}  "
              f"taste={item['taste_sim']:.3f}")

    # Generate page
    html = generate_page(selected)
    out = os.path.join(os.path.dirname(__file__), '..', 'website', 'recommendations.html')
    with open(out, 'w') as f:
        f.write(html)
    print(f"\nWrote {out}")

    # Save scores
    scores = [{'id': s['id'], 'score': s['effective_score'],
               'interest': s['interest'], 'taste': s['taste_sim']}
              for s in selected]
    scores_path = os.path.join(os.path.dirname(__file__), 'recommendation_scores.json')
    with open(scores_path, 'w') as f:
        json.dump(scores, f, indent=2)
    print(f"Wrote {scores_path}")


if __name__ == '__main__':
    main()
