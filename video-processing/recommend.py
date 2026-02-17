#!/usr/bin/env python3
"""
Analyze poster images and generate a recommendations page.
Scores non-curated clips on visual interest metrics and similarity to curated picks.
"""

import os
import sys
import json
import urllib.request
import numpy as np
from PIL import Image
from io import BytesIO
from collections import OrderedDict

CDN = "https://d2xbllb3qhv8ay.cloudfront.net"

# Current curated clip IDs
CURATED = {
    "1164634955", "1164636125", "1164635021", "1164634924",
    "2026-02-14_19-17-30_t0015", "1164634856", "1164634995",
    "1164635062", "1164636298", "2026-02-14_20-09-42_t0035",
    "1164635880", "1164635143", "2026-02-14_18-28-08_t0010",
    "2026-02-14_20-09-42_t0000", "1164635371", "1164635843",
    "1164635008", "2026-02-14_18-23-56_t0005", "1164636340",
    "2026-02-14_18-28-45_t0045", "2026-02-14_20-25-04_t0130",
    "2026-02-14_18-31-26_t0000",
}

# All archive clip IDs (from browse pages)
ALL_CLIPS = []

def load_all_clips():
    """Parse clip IDs from the browse pages."""
    import re
    website_dir = os.path.join(os.path.dirname(__file__), '..', 'website')
    for i in range(1, 13):
        path = os.path.join(website_dir, f'clips-{i}.html')
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            ids = re.findall(r'data-id="([^"]+)"', content)
            for cid in ids:
                if cid not in ALL_CLIPS:
                    ALL_CLIPS.append(cid)
    print(f"Total archive clips: {len(ALL_CLIPS)}")
    print(f"Already curated: {len(CURATED)}")
    candidates = [c for c in ALL_CLIPS if c not in CURATED]
    print(f"Candidates to analyze: {len(candidates)}")
    return candidates


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


def analyze_image(img):
    """Compute visual interest metrics for an image."""
    arr = np.array(img, dtype=np.float32)
    h, w, _ = arr.shape

    # Resize to standard size for consistent analysis
    if w > 384:
        img_resized = img.resize((384, 216), Image.LANCZOS)
        arr = np.array(img_resized, dtype=np.float32)

    # 1. Color richness: standard deviation across color channels
    color_std = np.mean([arr[:,:,c].std() for c in range(3)])

    # 2. Overall brightness
    brightness = arr.mean() / 255.0

    # 3. Contrast: difference between bright and dark regions
    gray = arr.mean(axis=2)
    p5, p95 = np.percentile(gray, 5), np.percentile(gray, 95)
    contrast = (p95 - p5) / 255.0

    # 4. Color saturation (in HSV-like space)
    maxc = arr.max(axis=2)
    minc = arr.min(axis=2)
    delta = maxc - minc
    # Avoid division by zero
    sat_map = np.where(maxc > 0, delta / maxc, 0)
    saturation = sat_map.mean()

    # 5. Spatial complexity: edge density via gradient magnitude
    gx = np.diff(gray, axis=1)
    gy = np.diff(gray, axis=0)
    # Trim to same shape
    min_h = min(gx.shape[0], gy.shape[0])
    min_w = min(gx.shape[1], gy.shape[1])
    grad_mag = np.sqrt(gx[:min_h, :min_w]**2 + gy[:min_h, :min_w]**2)
    complexity = grad_mag.mean() / 255.0

    # 6. Color diversity: number of distinct hue clusters
    # Quantize to 12 hue bins
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    hue_approx = np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)
    hue_bins = np.histogram(hue_approx[sat_map > 0.1].flatten(), bins=12)[0]
    hue_bins_norm = hue_bins / (hue_bins.sum() + 1e-8)
    color_diversity = -np.sum(hue_bins_norm * np.log(hue_bins_norm + 1e-8))  # entropy

    # 7. Quadrant color features (for similarity matching)
    mid_h, mid_w = h // 2, w // 2
    quadrants = [
        arr[:mid_h, :mid_w],
        arr[:mid_h, mid_w:],
        arr[mid_h:, :mid_w],
        arr[mid_h:, mid_w:],
    ]
    quad_features = np.array([q.mean(axis=(0,1)) / 255.0 for q in quadrants]).flatten()  # 12 values

    return {
        'color_std': float(color_std),
        'brightness': float(brightness),
        'contrast': float(contrast),
        'saturation': float(saturation),
        'complexity': float(complexity),
        'color_diversity': float(color_diversity),
        'quad_features': quad_features,  # numpy array, 12 floats
    }


def compute_composite_score(metrics, curated_features):
    """
    Compute a composite interest score.
    Higher = more visually interesting and/or similar to curated picks.
    """
    # Visual interest component (0-1 range each, weighted)
    interest = (
        metrics['contrast'] * 0.20 +
        metrics['saturation'] * 0.20 +
        metrics['complexity'] * 0.15 +
        metrics['color_diversity'] / 2.5 * 0.15 +  # normalize entropy to ~0-1
        # Penalize very dark or very bright (prefer mid-range)
        (1.0 - abs(metrics['brightness'] - 0.4) * 2) * 0.10 +
        metrics['color_std'] / 80.0 * 0.20  # normalize to ~0-1
    )

    # Similarity to curated picks component
    if len(curated_features) > 0:
        qf = metrics['quad_features']
        distances = [np.linalg.norm(qf - cf) for cf in curated_features]
        min_dist = min(distances)
        # Convert distance to similarity (closer = higher score)
        # Typical distances range 0-2, so similarity = 1 / (1 + dist)
        similarity = 1.0 / (1.0 + min_dist * 2)
    else:
        similarity = 0.5

    # Composite: 60% visual interest, 40% similarity to curated taste
    composite = interest * 0.6 + similarity * 0.4

    return float(composite), float(interest), float(similarity)


def generate_recommendations_page(ranked_clips, top_n=60):
    """Generate an HTML page with recommended clips."""
    clips = ranked_clips[:top_n]

    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>sublingualism — recommendations</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #000; color: #fff; font-family: monospace; }
        .header {
            padding: 20px;
            text-align: center;
        }
        .header h1 { font-size: 14px; font-weight: normal; letter-spacing: 0.2em; }
        .header p { font-size: 11px; color: #666; margin-top: 8px; }
        .nav {
            text-align: center;
            padding: 0 20px 20px;
            font-size: 12px;
        }
        .nav a {
            color: #666;
            text-decoration: none;
            margin: 0 10px;
        }
        .nav a:hover { color: #fff; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 2px;
            padding: 0 2px;
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
        .clip .score-badge {
            position: absolute;
            top: 4px;
            right: 4px;
            background: rgba(0,0,0,0.7);
            color: #aaa;
            font-size: 9px;
            padding: 2px 5px;
            border-radius: 3px;
            pointer-events: none;
            font-family: monospace;
        }
        .section-label {
            padding: 20px 10px 8px;
            font-size: 11px;
            color: #555;
            letter-spacing: 0.1em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>RECOMMENDATIONS</h1>
        <p>scored by visual interest + similarity to curated picks</p>
    </div>
    <div class="nav">
        <a href="clips.html">curated</a>
        <a href="clips-all.html">archive</a>
    </div>
""")

    # Top tier
    html_parts.append('    <div class="section-label">top picks</div>\n')
    html_parts.append('    <div class="grid">\n')
    for i, (cid, score, interest, similarity) in enumerate(clips[:20]):
        html_parts.append(f'            <div class="clip" data-id="{cid}" data-src="{CDN}/video/{cid}.mp4#t=0.001">')
        html_parts.append(f'<img src="{CDN}/posters/{cid}.jpg" alt="" onload="this.parentNode.classList.add(\'loaded\')">')
        html_parts.append(f'<span class="score-badge">{score:.2f}</span>')
        html_parts.append('</div>\n')
    html_parts.append('    </div>\n')

    # More to consider
    if len(clips) > 20:
        html_parts.append('    <div class="section-label">more to consider</div>\n')
        html_parts.append('    <div class="grid">\n')
        for i, (cid, score, interest, similarity) in enumerate(clips[20:]):
            html_parts.append(f'            <div class="clip" data-id="{cid}" data-src="{CDN}/video/{cid}.mp4#t=0.001">')
            html_parts.append(f'<img src="{CDN}/posters/{cid}.jpg" alt="" onload="this.parentNode.classList.add(\'loaded\')">')
            html_parts.append(f'<span class="score-badge">{score:.2f}</span>')
            html_parts.append('</div>\n')
        html_parts.append('    </div>\n')

    html_parts.append("""
    <script src="review.js"></script>
</body>
</html>
""")

    return ''.join(html_parts)


def main():
    candidates = load_all_clips()

    # First, analyze curated clips to build taste profile
    print("\nAnalyzing curated clips for taste profile...")
    curated_features = []
    for cid in CURATED:
        img = download_poster(cid)
        if img:
            metrics = analyze_image(img)
            curated_features.append(metrics['quad_features'])
            sys.stdout.write('.')
            sys.stdout.flush()
    print(f"\nGot features for {len(curated_features)} curated clips")

    # Analyze all candidates
    print(f"\nAnalyzing {len(candidates)} candidate clips...")
    results = []
    for i, cid in enumerate(candidates):
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(candidates)}...")
        img = download_poster(cid)
        if img is None:
            continue
        metrics = analyze_image(img)
        composite, interest, similarity = compute_composite_score(metrics, curated_features)
        results.append((cid, composite, interest, similarity))

    # Sort by composite score, descending
    results.sort(key=lambda x: x[1], reverse=True)

    print(f"\nTop 20 recommendations:")
    for i, (cid, score, interest, sim) in enumerate(results[:20]):
        print(f"  {i+1}. {cid}  score={score:.3f}  interest={interest:.3f}  similarity={sim:.3f}")

    # Generate the page
    html = generate_recommendations_page(results, top_n=60)
    output_path = os.path.join(os.path.dirname(__file__), '..', 'website', 'recommendations.html')
    with open(output_path, 'w') as f:
        f.write(html)
    print(f"\nWrote {output_path}")

    # Also save raw scores for reference
    scores_path = os.path.join(os.path.dirname(__file__), 'recommendation_scores.json')
    scores_data = [{'id': cid, 'score': s, 'interest': i, 'similarity': sim}
                   for cid, s, i, sim in results]
    with open(scores_path, 'w') as f:
        json.dump(scores_data, f, indent=2)
    print(f"Wrote scores to {scores_path}")


if __name__ == '__main__':
    main()
