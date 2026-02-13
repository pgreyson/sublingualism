#!/usr/bin/env python3
"""Local server for the segment picker GUI."""

import http.server
import json
import os
import subprocess
import urllib.parse
import mimetypes
import re

PORT = 8765
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")

class SegmentPickerHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        if path == "/":
            self.serve_file("index.html", "text/html")
        elif path == "/manifest.json":
            self.serve_file("manifest.json", "application/json")
        elif path.startswith("/thumbnails/"):
            filepath = os.path.join(BASE_DIR, path.lstrip("/"))
            if os.path.exists(filepath):
                self.serve_static(filepath)
            else:
                self.send_error(404)
        elif path == "/video":
            self.serve_video_range(params)
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/export":
            content_length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(content_length))
            self.handle_export(body)
        else:
            self.send_error(404)

    def serve_file(self, filename, content_type):
        filepath = os.path.join(BASE_DIR, filename)
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def serve_static(self, filepath):
        mime = mimetypes.guess_type(filepath)[0] or "application/octet-stream"
        with open(filepath, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(data))
        self.end_headers()
        self.wfile.write(data)

    def serve_video_range(self, params):
        """Serve a 10s clip from a video, transcoded to mp4 for browser playback."""
        video_path = params.get("path", [None])[0]
        start = params.get("start", ["0"])[0]
        duration = params.get("duration", ["10"])[0]

        if not video_path or not os.path.exists(video_path):
            self.send_error(404, "Video not found")
            return

        # Transcode the segment to mp4 for browser compatibility
        cmd = [
            "ffmpeg", "-v", "quiet",
            "-ss", start, "-i", video_path, "-t", duration,
            "-vf", "scale=1920:-1",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac", "-movflags", "frag_keyframe+empty_moov",
            "-f", "mp4", "pipe:1"
        ]
        result = subprocess.run(cmd, capture_output=True)

        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Length", len(result.stdout))
        self.end_headers()
        self.wfile.write(result.stdout)

    def handle_export(self, body):
        """Export selected segments as full-quality clips."""
        selections = body.get("selections", [])
        os.makedirs(EXPORT_DIR, exist_ok=True)

        results = []
        for sel in selections:
            video_path = sel["path"]
            start = sel["start"]
            duration = sel["duration"]
            video_id = sel["video_id"]
            index = sel["index"]

            out_name = f"{video_id}_seg{index:03d}.mp4"
            out_path = os.path.join(EXPORT_DIR, out_name)

            cmd = [
                "ffmpeg", "-v", "quiet", "-y",
                "-ss", str(start), "-i", video_path, "-t", str(duration),
                "-c", "copy", out_path
            ]
            subprocess.run(cmd)
            results.append({"file": out_name, "path": out_path})

        response = json.dumps({"exported": results}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        if "/video" not in str(args):
            super().log_message(format, *args)


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    server = http.server.HTTPServer(("", PORT), SegmentPickerHandler)
    print(f"Segment picker running at http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
