#!/usr/bin/env python3
"""Group clips by recording session, ordered by capture time, and generate browse pages."""

import os
import re
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), "website")
CDN = "https://d2xbllb3qhv8ay.cloudfront.net"
CLIPS_PER_PAGE = 20

# Pattern: 2026-02-09_21-35-26_t0230
CLIP_ID_RE = re.compile(r'^(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_t(\d+)$')


def parse_clip_id(clip_id):
    """Parse a clip ID into (session_key, timecode) or None for legacy IDs."""
    m = CLIP_ID_RE.match(clip_id)
    if m:
        return m.group(1), int(m.group(2))
    return None, None


def session_label(session_key):
    """Format a session key like '2026-02-09_21-35-26' into a readable label."""
    # 2026-02-09_21-35-26 -> Feb 9, 2026 9:35 PM
    parts = session_key.split('_')
    date_parts = parts[0].split('-')
    time_parts = parts[1].split('-')
    year, month, day = int(date_parts[0]), int(date_parts[1]), int(date_parts[2])
    hour, minute = int(time_parts[0]), int(time_parts[1])
    months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    ampm = 'AM' if hour < 12 else 'PM'
    h12 = hour % 12 or 12
    return f"{months[month]} {day}, {year} {h12}:{minute:02d} {ampm}"


def group_and_sort_clips(all_ids):
    """Group clips by recording session, sort by timecode within, newest session first.
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

    # Sort sessions newest first (session_key sorts chronologically as a string)
    sorted_sessions = sorted(sessions.keys(), reverse=True)

    # Build ordered list of (session_key_or_label, [clip_ids])
    result = []
    for key in sorted_sessions:
        clips = [cid for _, cid in sessions[key]]
        result.append((key, session_label(key), clips))

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
                <div class="session-label">{label}</div>
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

    # Group by recording session, sort by timecode, newest first
    sessions = group_and_sort_clips(all_ids)
    print(f"\nFound {len(sessions)} recording sessions:")
    for key, label, clips in sessions:
        print(f"  {label}: {len(clips)} clips")

    # Paginate: split each session into pages of CLIPS_PER_PAGE
    # Each page stays within one session
    pages = []  # list of (session_key, session_label, [clip_ids])
    for key, label, clips in sessions:
        for i in range(0, len(clips), CLIPS_PER_PAGE):
            pages.append((key, label, clips[i:i + CLIPS_PER_PAGE]))

    total_pages = len(pages)
    print(f"\nGenerating {total_pages} pages...")

    # Generate browse pages
    for page_num, (key, label, clips) in enumerate(pages, 1):
        html = generate_page_html(page_num, clips, total_pages)
        path = os.path.join(WEBSITE_DIR, f"clips-{page_num}.html")
        with open(path, "w") as f:
            f.write(html)
        print(f"  Generated clips-{page_num}.html ({len(clips)} clips, {label})")

    # Remove extra old pages
    for old_page in range(total_pages + 1, 50):
        old_path = os.path.join(WEBSITE_DIR, f"clips-{old_page}.html")
        if os.path.exists(old_path):
            os.remove(old_path)
            print(f"  Removed old clips-{old_page}.html")
        else:
            break

    # Build index: group pages by session
    sessions_with_pages = []  # list of (label, [(page_num, clips)])
    current_session = None
    for page_num, (key, label, clips) in enumerate(pages, 1):
        if current_session is None or current_session[0] != key:
            current_session = (key, label, [])
            sessions_with_pages.append(current_session)
        current_session[2].append((page_num, clips))

    index_data = [(label, page_groups) for key, label, page_groups in sessions_with_pages]
    index_html = generate_index_html(index_data)
    index_path = os.path.join(WEBSITE_DIR, "clips-all.html")
    with open(index_path, "w") as f:
        f.write(index_html)
    print(f"  Generated clips-all.html")

    print(f"\nDone! {len(all_ids)} clips across {total_pages} pages, {len(sessions_with_pages)} sessions")


if __name__ == "__main__":
    main()
