#!/usr/bin/env python3
"""Serve the Content Freshness Radar webapp and run the pipeline via /api/scan.

Usage:
    python3 server.py          # http://localhost:8777
    python3 server.py 8080     # custom port
"""

import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from run_pipeline import process  # noqa: E402

WEBAPP = os.path.join(ROOT, "webapp")

MIME = {
    ".html":  "text/html; charset=utf-8",
    ".js":    "application/javascript; charset=utf-8",
    ".css":   "text/css; charset=utf-8",
    ".json":  "application/json; charset=utf-8",
    ".png":   "image/png",
    ".svg":   "image/svg+xml",
    ".ico":   "image/x-icon",
    ".woff2": "font/woff2",
    ".woff":  "font/woff",
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/scan":
            self._handle_scan(parsed.query)
            return

        rel = parsed.path.lstrip("/") or "index.html"
        file_path = os.path.realpath(os.path.join(WEBAPP, *rel.split("/")))
        if not file_path.startswith(os.path.realpath(WEBAPP)):
            self.send_error(403)
            return
        if not os.path.isfile(file_path):
            self.send_error(404)
            return

        ext = os.path.splitext(file_path)[1].lower()
        with open(file_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_scan(self, query_string):
        params = urllib.parse.parse_qs(query_string)

        def p(key, default=""):
            return (params.get(key) or [default])[0].strip()

        category = p("category")
        if not category:
            return self._json_error(400, "category is required")

        wiki = p("wiki", "en.wikipedia.org")
        try:
            limit = min(max(1, int(p("limit", "30"))), 100)
            depth = min(max(1, int(p("depth", "2"))), 4)
        except ValueError:
            return self._json_error(400, "limit and depth must be integers")

        recursive = p("recursive", "false").lower() == "true"

        print(f"\n[scan] Category:'{category}' on {wiki} "
              f"(limit={limit}, recursive={recursive})")
        try:
            data = process(wiki, category, limit, False, 60, recursive, depth)
        except Exception as exc:
            print(f"[scan] Failed: {exc}")
            return self._json_error(500, str(exc))

        out_path = os.path.join(WEBAPP, "data.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
        print(f"[scan] Done — {data['article_count']} articles, "
              f"{data['needs_update_count']} with update evidence")

    def _json_error(self, code, message):
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # scan events logged above; suppress static-file noise


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8777
    print(f"Content Freshness Radar  →  http://localhost:{port}")
    print("Press Ctrl+C to stop.\n")
    try:
        HTTPServer(("", port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
