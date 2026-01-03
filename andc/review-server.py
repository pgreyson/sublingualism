#!/usr/bin/env python3
"""
Web-based photo reviewer for solstice/equinox photos.
Run this and open http://localhost:8000 in your browser.
"""

from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
import urllib.parse
import subprocess
import tempfile
import hashlib

PORT = 8000
BASE_DIR = "/Volumes/Workspace/sublingualism/andc"
INPUT_FILE = os.path.join(BASE_DIR, "solstice-equinox-photos.txt")
SELECTED_FILE = os.path.join(BASE_DIR, "selected-photos.txt")
REJECTED_FILE = os.path.join(BASE_DIR, "rejected-photos.txt")

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.tif', '.tiff', '.heic', '.webp', '.bmp', '.cr2', '.nef', '.arw', '.dng'}
RAW_EXTENSIONS = {'.cr2', '.nef', '.arw', '.dng', '.tif', '.tiff', '.heic'}
CACHE_DIR = os.path.join(BASE_DIR, ".preview_cache")

def is_image(path):
    ext = os.path.splitext(path.lower())[1]
    return ext in IMAGE_EXTENSIONS

def load_list(filepath, filter_images=False):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            if filter_images:
                lines = [l for l in lines if is_image(l)]
            return lines
    return []

def save_list(filepath, items):
    with open(filepath, 'w') as f:
        f.write('\n'.join(sorted(items)))

class ReviewHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())

        elif parsed.path == '/api/photos':
            photos = load_list(INPUT_FILE, filter_images=True)
            selected = set(load_list(SELECTED_FILE))
            rejected = set(load_list(REJECTED_FILE))

            data = {
                'photos': photos,
                'selected': list(selected),
                'rejected': list(rejected)
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

        elif parsed.path.startswith('/photo/'):
            # Serve the actual image file
            photo_path = urllib.parse.unquote(parsed.path[7:])  # Remove '/photo/'
            if os.path.exists(photo_path):
                ext = os.path.splitext(photo_path.lower())[1]

                # Check if we need to convert RAW/HEIC files
                if ext in RAW_EXTENSIONS:
                    # Create cache dir if needed
                    os.makedirs(CACHE_DIR, exist_ok=True)

                    # Generate cache filename based on path hash
                    path_hash = hashlib.md5(photo_path.encode()).hexdigest()
                    cache_file = os.path.join(CACHE_DIR, f"{path_hash}.jpg")

                    # Convert if not cached
                    if not os.path.exists(cache_file):
                        try:
                            subprocess.run([
                                'sips', '-s', 'format', 'jpeg',
                                '-s', 'formatOptions', '80',
                                '--resampleHeight', '1200',
                                photo_path, '--out', cache_file
                            ], capture_output=True, check=True)
                        except subprocess.CalledProcessError:
                            self.send_error(500, "Failed to convert image")
                            return

                    # Serve cached JPEG
                    self.send_response(200)
                    self.send_header('Content-type', 'image/jpeg')
                    self.end_headers()
                    with open(cache_file, 'rb') as f:
                        self.wfile.write(f.read())
                else:
                    # Serve regular image files directly
                    self.send_response(200)
                    content_type = {
                        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                        '.png': 'image/png', '.gif': 'image/gif',
                        '.webp': 'image/webp', '.bmp': 'image/bmp'
                    }.get(ext, 'image/jpeg')
                    self.send_header('Content-type', content_type)
                    self.end_headers()
                    with open(photo_path, 'rb') as f:
                        self.wfile.write(f.read())
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == '/api/select':
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length))
            photo = post_data['photo']
            action = post_data['action']

            selected = set(load_list(SELECTED_FILE))
            rejected = set(load_list(REJECTED_FILE))

            filename = os.path.basename(photo)
            if action == 'yes':
                selected.add(photo)
                rejected.discard(photo)
                print(f"YES: {filename}  (total selected: {len(selected)})")
            elif action == 'no':
                rejected.add(photo)
                selected.discard(photo)
                print(f"NO:  {filename}  (total rejected: {len(rejected)})")
            elif action == 'undo':
                selected.discard(photo)
                rejected.discard(photo)
                print(f"UNDO: {filename}")

            save_list(SELECTED_FILE, selected)
            save_list(REJECTED_FILE, rejected)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        # Suppress logging for cleaner output
        pass

HTML_PAGE = '''<!DOCTYPE html>
<html>
<head>
    <title>ANDC Photo Reviewer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #1a1a1a;
            color: #fff;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 15px;
            text-align: center;
            background: #252525;
        }
        .status {
            font-size: 18px;
            margin-bottom: 5px;
        }
        .filename {
            font-size: 12px;
            color: #888;
            word-break: break-all;
        }
        .image-container {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            overflow: hidden;
        }
        .image-container img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        .controls {
            padding: 20px;
            display: flex;
            justify-content: center;
            gap: 15px;
            background: #252525;
        }
        button {
            font-size: 18px;
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.1s;
        }
        button:hover { transform: scale(1.05); }
        button:active { transform: scale(0.95); }
        .btn-no { background: #cc4444; color: white; }
        .btn-nav { background: #444; color: white; }
        .btn-yes { background: #44aa44; color: white; }
        .selected { box-shadow: 0 0 0 4px #44aa44; }
        .rejected { box-shadow: 0 0 0 4px #cc4444; opacity: 0.6; }
        .keys {
            font-size: 12px;
            color: #666;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="status" id="status">Loading...</div>
        <div class="filename" id="filename"></div>
    </div>
    <div class="image-container" id="imageContainer">
        <img id="photo" src="" alt="Photo">
    </div>
    <div class="controls">
        <button class="btn-no" onclick="reject()">NO (N)</button>
        <button class="btn-nav" onclick="prev()">&larr; Prev</button>
        <button class="btn-nav" onclick="next()">Next &rarr;</button>
        <button class="btn-yes" onclick="select()">YES (Y)</button>
    </div>
    <div class="keys" style="text-align:center;padding-bottom:10px;">
        Keys: Y=Yes, N=No, Arrow keys=Navigate, U=Undo
    </div>

    <script>
        let photos = [];
        let selected = new Set();
        let rejected = new Set();
        let currentIndex = 0;

        async function load() {
            const resp = await fetch('/api/photos');
            const data = await resp.json();
            photos = data.photos;
            selected = new Set(data.selected);
            rejected = new Set(data.rejected);

            // Find first unreviewed
            currentIndex = photos.findIndex(p => !selected.has(p) && !rejected.has(p));
            if (currentIndex === -1) currentIndex = 0;

            show();
        }

        function show() {
            if (photos.length === 0) {
                document.getElementById('status').textContent = 'No photos found';
                return;
            }

            const photo = photos[currentIndex];
            const img = document.getElementById('photo');
            img.src = '/photo/' + encodeURIComponent(photo);
            img.className = selected.has(photo) ? 'selected' : rejected.has(photo) ? 'rejected' : '';

            document.getElementById('filename').textContent = photo;

            let status = `${currentIndex + 1} / ${photos.length}  |  Yes: ${selected.size}  No: ${rejected.size}`;
            if (selected.has(photo)) status += '  [SELECTED]';
            if (rejected.has(photo)) status += '  [REJECTED]';
            document.getElementById('status').textContent = status;
        }

        async function doAction(action) {
            const photo = photos[currentIndex];
            await fetch('/api/select', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({photo, action})
            });

            if (action === 'yes') {
                selected.add(photo);
                rejected.delete(photo);
            } else if (action === 'no') {
                rejected.add(photo);
                selected.delete(photo);
            } else if (action === 'undo') {
                selected.delete(photo);
                rejected.delete(photo);
            }
        }

        async function select() {
            await doAction('yes');
            next();
        }

        async function reject() {
            await doAction('no');
            next();
        }

        async function undo() {
            await doAction('undo');
            show();
        }

        function next() {
            if (currentIndex < photos.length - 1) {
                currentIndex++;
                show();
            }
        }

        function prev() {
            if (currentIndex > 0) {
                currentIndex--;
                show();
            }
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'y' || e.key === 'Y') select();
            else if (e.key === 'n' || e.key === 'N') reject();
            else if (e.key === 'u' || e.key === 'U') undo();
            else if (e.key === 'ArrowLeft') prev();
            else if (e.key === 'ArrowRight') next();
        });

        load();
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print(f"Starting photo reviewer at http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    print()
    print("Keys: Y=Yes, N=No, Arrow keys=Navigate, U=Undo")

    httpd = HTTPServer(('localhost', PORT), ReviewHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
