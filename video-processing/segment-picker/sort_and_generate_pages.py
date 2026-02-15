#!/usr/bin/env python3
"""Group clips by recording session, ordered by capture time, and generate browse pages."""

import os
import re
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "website")
CDN = "https://d2xbllb3qhv8ay.cloudfront.net"
CLIPS_PER_PAGE = 20
MERGE_WINDOW_MINUTES = 30  # merge sessions starting within this window

# Pattern: 2026-02-09_21-35-26_t0230
CLIP_ID_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_t(\d+)$')


def parse_clip_id(clip_id):
    """Parse a clip ID into (session_key, timecode) or None for legacy IDs."""
    m = CLIP_ID_RE.match(clip_id)
    if m:
        return m.group(1), int(m.group(2))
    return None, None


def session_key_to_datetime(session_key):
    """Convert '2026-02-09_21-35-26' to a datetime."""
    return datetime.strptime(session_key, '%Y-%m-%d_%H-%M-%S')


def session_label(session_key):
    """Format a session key like '2026-02-09_21-35-26' into a readable label."""
    dt = session_key_to_datetime(session_key)
    return dt.strftime('%b %-d, %Y %-I:%M %p')


def session_range_label(keys):
    """Label for a merged group of sessions on the same date."""
    dts = sorted(session_key_to_datetime(k) for k in keys)
    first, last = dts[0], dts[-1]
    if first.date() == last.date():
        date_str = first.strftime('%b %-d, %Y')
        if len(keys) == 1:
            return f"{date_str} {first.strftime('%-I:%M %p')}"
        return f"{date_str} {first.strftime('%-I:%M')}–{last.strftime('%-I:%M %p')}"
    return f"{first.strftime('%b %-d')}–{last.strftime('%b %-d, %Y')}"


def group_and_sort_clips(all_ids):
    """Group clips by recording session, merge nearby sessions, newest first.
    Legacy numeric IDs go in a separate group at the end."""
    sessions = defaultdict(list)
    legacy = []

    for cid in all_ids:
        session_key, timecode = parse_clip_id(cid)
        if session_key:
            sessions[session_key].append((timecode, cid))
        else:
            legacy.append(cid)

    # Sort clips within each session by timecode
    for key in sessions:
        sessions[key].sort(key=lambda x: x[0])

    # Sort sessions newest first
    sorted_keys = sorted(sessions.keys(), reverse=True)

    # Merge sessions that start within MERGE_WINDOW_MINUTES of each other
    merged = []  # list of (group_keys, all_clip_ids)
    for key in sorted_keys:
        clips = [cid for _, cid in sessions[key]]
        dt = session_key_to_datetime(key)

        if merged:
            # Check if this session is close to the previous group's latest session
            prev_keys, prev_clips = merged[-1]
            prev_dt = min(session_key_to_datetime(k) for k in prev_keys)  # earliest in group (since we go newest-first)
            diff = abs((prev_dt - dt).total_seconds()) / 60
            if diff <= MERGE_WINDOW_MINUTES:
                prev_keys.append(key)
                prev_clips.extend(clips)
                continue

        merged.append(([key], clips))

    # Build result with labels
    result = []
    for keys, clips in merged:
        # Sort clips within merged group by their full ID (session + timecode)
        clips.sort(key=lambda cid: cid)
        label = session_range_label(keys)
        group_key = keys[0]  # use newest session key as the group key
        result.append((group_key, label, clips))

    if legacy:
        result.append(('legacy', 'earlier sessions', legacy))

    return result


def generate_page_html(page_num, clips, total_pages):
    """Generate HTML for a browse page."""
    clips_html = "\n".join(
        f'            <div class="clip" data-id="{cid}">\n'
        f'                <video src="{CDN}/video/{cid}.mp4#t=0.001" poster="{CDN}/posters/{cid}.jpg" preload="none" loop muted playsinline></video>\n'
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
            object-fit: cover;
        }}
        .page-nav {{
            margin-top: 2rem;
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
            align-items: center;
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
        .page-nav .prev-next {{
            opacity: 0.7;
            font-size: 0.9rem;
        }}
        .page-nav .prev-next:hover {{
            opacity: 1;
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
            {f'<a class="prev-next" href="/clips-{page_num - 1}.html">&larr; prev</a>' if page_num > 1 else '<span></span>'} {page_nav} {f'<a class="prev-next" href="/clips-{page_num + 1}.html">next &rarr;</a>' if page_num < total_pages else ''}
        </div>
    </div>
    <script src="/review.js"></script>
</body>
</html>
'''


def generate_index_html(sessions_with_pages):
    """Generate clips-all.html with one row per recording session.

    sessions_with_pages: list of (label, [(page_num, clips)])
    """
    rows = []
    for label, page_groups in sessions_with_pages:
        total_clips = sum(len(clips) for _, clips in page_groups)
        # For each session, show links to its pages with thumbnail previews
        page_cards = []
        for page_num, clips in page_groups:
            count = len(clips)
            # Sample up to 6 thumbnails
            indices = list(range(min(count, 6))) if count <= 6 else [int(i * count / 6) for i in range(6)]
            thumbs = "\n".join(
                f'                        <img src="{CDN}/posters/{clips[i]}.jpg" alt="" loading="lazy">'
                for i in indices
            )
            page_cards.append(f'''                <a class="page-link" href="/clips-{page_num}.html">
                    <div class="header">
                        <div class="count">{count} clips</div>
                    </div>
                    <div class="thumbs">
{thumbs}
                    </div>
                </a>''')

        cards_html = "\n".join(page_cards)
        rows.append(f'''            <div class="session">
                <div class="session-label">{label} <span class="session-total">{total_clips} clips</span></div>
                <div class="session-pages">
{cards_html}
                </div>
            </div>''')

    rows_html = "\n".join(rows)

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
        .sessions {{
            display: flex;
            flex-direction: column;
            gap: 2rem;
            margin-top: 1rem;
        }}
        .session-label {{
            font-size: 1.1rem;
            opacity: 0.7;
            margin-bottom: 0.75rem;
        }}
        .session-total {{
            opacity: 0.5;
            font-size: 0.85rem;
        }}
        .session-pages {{
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }}
        .page-link {{
            display: block;
            border: 1px solid rgba(255,255,255,0.2);
            padding: 0.75rem;
            text-decoration: none;
            color: #fff;
            transition: border-color 0.2s;
            width: 300px;
        }}
        .page-link:hover {{
            border-color: rgba(255,255,255,0.6);
        }}
        .page-link .header {{
            margin-bottom: 0.5rem;
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
        <div class="sessions">
{rows_html}
        </div>
    </div>
</body>
</html>
'''


def main():
    # Collect all clip IDs from existing pages + new from scan
    existing_ids = []
    for page_num in range(1, 100):
        page_file = os.path.join(WEBSITE_DIR, f"clips-{page_num}.html")
        if not os.path.exists(page_file):
            break
        with open(page_file) as f:
            content = f.read()
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

    # Group by recording session, merge nearby, sort by timecode, newest first
    sessions = group_and_sort_clips(all_ids)
    print(f"\nFound {len(sessions)} session groups:")
    for key, label, clips in sessions:
        print(f"  {label}: {len(clips)} clips")

    # Paginate: pages can span sessions, just fill to CLIPS_PER_PAGE
    all_clips_ordered = []
    for key, label, clips in sessions:
        all_clips_ordered.extend(clips)

    pages = []
    for i in range(0, len(all_clips_ordered), CLIPS_PER_PAGE):
        pages.append(all_clips_ordered[i:i + CLIPS_PER_PAGE])

    total_pages = len(pages)
    print(f"\nGenerating {total_pages} pages...")

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

    # Build index: map session groups to their page ranges
    # Figure out which pages each session group lands on
    clip_page_map = {}  # clip_id -> page_num
    for page_num, clips in enumerate(pages, 1):
        for cid in clips:
            clip_page_map[cid] = page_num

    sessions_with_pages = []
    for key, label, clips in sessions:
        # Find all pages this session spans
        page_clips = defaultdict(list)
        for cid in clips:
            pn = clip_page_map[cid]
            page_clips[pn].append(cid)
        page_groups = sorted(page_clips.items())
        sessions_with_pages.append((label, page_groups))

    index_html = generate_index_html(sessions_with_pages)
    index_path = os.path.join(WEBSITE_DIR, "clips-all.html")
    with open(index_path, "w") as f:
        f.write(index_html)
    print(f"  Generated clips-all.html")

    print(f"\nDone! {len(all_ids)} clips across {total_pages} pages, {len(sessions)} session groups")


if __name__ == "__main__":
    main()
