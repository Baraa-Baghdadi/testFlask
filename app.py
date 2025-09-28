#!/usr/bin/env python3
"""
Flask minimal server: download to temp, stream back to client, then delete temp files.
"""

import os
import shutil
import tempfile
import logging
from pathlib import Path
from datetime import datetime

from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS

try:
    import yt_dlp
except Exception:
    raise SystemExit("yt-dlp required. Install with: pip install yt-dlp")

app = Flask(__name__)
CORS(app)

# simple logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("video-api")

@app.route('/api/direct-download-temp', methods=['POST'])
def direct_download_temp():
    """
    Download video into a temporary directory, stream it back to client, then delete.
    Request body (JSON): { "url": "...", "quality": "best" }
    """
    data = request.get_json() or {}
    url = data.get('url')
    quality = data.get('quality', 'best')

    if not url:
        return jsonify({'error': 'url is required'}), 400

    temp_dir = tempfile.mkdtemp(prefix='vd_')
    logger.info("Created temp dir %s for URL %s", temp_dir, url)

    try:
        # yt-dlp options - save into temp dir, restricted filenames to avoid windows issues
        outtmpl = os.path.join(temp_dir, '%(title)s.%(ext)s')
        ydl_opts = {
            'format': quality,
            'outtmpl': outtmpl,
            'quiet': True,            # reduce console spam
            'no_warnings': True,
            'restrictfilenames': True,
            'noplaylist': False,      # allow playlists if the user provided one
            'retries': 3,
            'merge_output_format': 'mp4',  # when separate streams need merging
        }

        logger.info("Starting yt-dlp download (this may take a while)...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)

        # find downloaded file(s)
        files = [p for p in Path(temp_dir).iterdir() if p.is_file()]
        if not files:
            raise RuntimeError("No file produced by yt-dlp")

        # pick largest file (usually the video)
        file_path = max(files, key=lambda p: p.stat().st_size)
        logger.info("Downloaded file: %s (size=%d)", file_path.name, file_path.stat().st_size)

        # schedule cleanup after response is fully sent
        @after_this_request
        def cleanup(response):
            try:
                shutil.rmtree(temp_dir)
                logger.info("Cleaned up temp dir %s", temp_dir)
            except Exception:
                logger.exception("Failed to cleanup temp dir %s", temp_dir)
            return response

        # stream file as an attachment (browser or curl will save it)
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.name
        )

    except Exception as e:
        logger.exception("Error in direct_download_temp")
        # try to cleanup on error
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
