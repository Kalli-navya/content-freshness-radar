#!/usr/bin/env python3

import json
import os
import sys

from flask import Flask, request, jsonify, send_from_directory

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from run_pipeline import process

WEBAPP = os.path.join(ROOT, "webapp")

app = Flask(
    __name__,
    static_folder=WEBAPP,
    static_url_path=""
)


@app.route("/")
def index():
    return send_from_directory(WEBAPP, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(WEBAPP, path)


@app.route("/api/scan")
def scan():

    category = request.args.get("category", "").strip()

    if not category:
        return jsonify({"error": "category is required"}), 400

    wiki = request.args.get("wiki", "en.wikipedia.org")

    try:
        limit = min(max(1, int(request.args.get("limit", 30))), 100)
        depth = min(max(1, int(request.args.get("depth", 2))), 4)
    except ValueError:
        return jsonify({"error": "limit and depth must be integers"}), 400

    recursive = (
        request.args.get("recursive", "false").lower() == "true"
    )

    try:

        data = process(
            wiki,
            category,
            limit,
            False,
            60,
            recursive,
            depth,
        )

        with open(
            os.path.join(WEBAPP, "data.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False,
            )

        return jsonify(data)

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
