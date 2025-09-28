#!/usr/bin/env python3
"""
Flask Video Downloader API
A RESTful API for downloading videos from various platforms
"""

import os
import sys
import uuid
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, send_file, abort
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
import logging
from logging.handlers import RotatingFileHandler

# Import your existing VideoDownloader class
from video_downloader import VideoDownloader

app = Flask(__name__)
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size
app.config['DOWNLOADS_DIR'] = os.environ.get('DOWNLOADS_DIR', 'downloads')
app.config['TEMP_DIR'] = os.environ.get('TEMP_DIR', 'temp')
app.config['MAX_CONCURRENT_DOWNLOADS'] = int(os.environ.get('MAX_CONCURRENT_DOWNLOADS', '3'))
app.config['CLEANUP_INTERVAL_HOURS'] = int(os.environ.get('CLEANUP_INTERVAL_HOURS', '24'))

# Global variables for tracking downloads
active_downloads: Dict[str, Dict[str, Any]] = {}
download_lock = threading.Lock()

# Setup logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/api.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Video Downloader API startup')

# Create necessary directories
Path(app.config['DOWNLOADS_DIR']).mkdir(exist_ok=True)
Path(app.config['TEMP_DIR']).mkdir(exist_ok=True)


class DownloadManager:
    """Manages download tasks and cleanup"""
    
    def __init__(self):
        self.cleanup_thread = threading.Thread(target=self._cleanup_old_files, daemon=True)
        self.cleanup_thread.start()
    
    def _cleanup_old_files(self):
        """Background task to cleanup old downloaded files"""
        while True:
            try:
                cleanup_time = datetime.now() - timedelta(hours=app.config['CLEANUP_INTERVAL_HOURS'])
                downloads_dir = Path(app.config['DOWNLOADS_DIR'])
                
                for file_path in downloads_dir.rglob('*'):
                    if file_path.is_file():
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cleanup_time:
                            try:
                                file_path.unlink()
                                app.logger.info(f"Cleaned up old file: {file_path}")
                            except Exception as e:
                                app.logger.error(f"Failed to cleanup file {file_path}: {e}")
                
                # Sleep for 1 hour before next cleanup
                time.sleep(3600)
            except Exception as e:
                app.logger.error(f"Error in cleanup thread: {e}")
                time.sleep(3600)

# Initialize download manager
download_manager = DownloadManager()


def download_worker(download_id: str, url: str, options: Dict[str, Any]):
    """Worker function for downloading videos in background"""
    try:
        with download_lock:
            active_downloads[download_id]['status'] = 'downloading'
            active_downloads[download_id]['started_at'] = datetime.now().isoformat()
        
        # Create downloader instance
        downloader = VideoDownloader(
            output_dir=os.path.join(app.config['DOWNLOADS_DIR'], download_id),
            quality=options.get('quality', 'best')
        )
        
        # Download video
        if options.get('playlist', False):
            success = downloader.download_playlist(
                url, 
                options.get('max_downloads')
            )
        else:
            success = downloader.download_video(
                url,
                options.get('audio_only', False),
                options.get('subtitles')
            )
        
        with download_lock:
            if success:
                active_downloads[download_id]['status'] = 'completed'
                active_downloads[download_id]['completed_at'] = datetime.now().isoformat()
                
                # List downloaded files
                download_dir = Path(app.config['DOWNLOADS_DIR']) / download_id
                files = [f.name for f in download_dir.iterdir() if f.is_file()]
                active_downloads[download_id]['files'] = files
            else:
                active_downloads[download_id]['status'] = 'failed'
                active_downloads[download_id]['error'] = 'Download failed'
                
    except Exception as e:
        app.logger.error(f"Download error for {download_id}: {e}")
        with download_lock:
            active_downloads[download_id]['status'] = 'failed'
            active_downloads[download_id]['error'] = str(e)


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({'error': 'Request too large'}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'active_downloads': len(active_downloads),
        'version': '1.0.0'
    })


@app.route('/api/info', methods=['POST'])
def get_video_info():
    """Get video information without downloading"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url']
        
        # Create temporary downloader instance
        downloader = VideoDownloader(output_dir=app.config['TEMP_DIR'])
        info = downloader.get_video_info(url)
        
        if info:
            return jsonify({
                'success': True,
                'info': info
            })
        else:
            return jsonify({'error': 'Failed to extract video information'}), 400
            
    except Exception as e:
        app.logger.error(f"Info extraction error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/formats', methods=['POST'])
def get_video_formats():
    """Get available video formats"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url']
        
        # Create temporary downloader instance
        downloader = VideoDownloader(output_dir=app.config['TEMP_DIR'])
        formats = downloader.get_available_formats(url)
        
        if formats:
            return jsonify({
                'success': True,
                'formats': formats
            })
        else:
            return jsonify({'error': 'Failed to extract format information'}), 400
            
    except Exception as e:
        app.logger.error(f"Format extraction error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/download', methods=['POST'])
def start_download():
    """Start video download and wait until finished, then return download ID and .mp4 files"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400

        # Check concurrent downloads limit
        active_count = len([d for d in active_downloads.values() 
                           if d['status'] in ['queued', 'downloading']])
        
        if active_count >= app.config['MAX_CONCURRENT_DOWNLOADS']:
            return jsonify({
                'error': f'Maximum concurrent downloads ({app.config["MAX_CONCURRENT_DOWNLOADS"]}) reached'
            }), 429

        # Generate unique download ID
        download_id = str(uuid.uuid4())
        
        # Prepare download options
        options = {
            'quality': data.get('quality', 'best'),
            'audio_only': data.get('audio_only', False),
            'subtitles': data.get('subtitles'),
            'playlist': data.get('playlist', False),
            'max_downloads': data.get('max_downloads')
        }

        # Store download info
        with download_lock:
            active_downloads[download_id] = {
                'url': data['url'],
                'status': 'queued',
                'created_at': datetime.now().isoformat(),
                'options': options,
                'files': []
            }

        # --- Synchronous download ---
        download_worker(download_id, data['url'], options)

        # Fetch completed download info
        download_info = active_downloads[download_id]
        if download_info['status'] != 'completed':
            return jsonify({
                'success': False,
                'download_id': download_id,
                'status': download_info['status'],
                'error': download_info.get('error', 'Unknown error')
            }), 500

        # Filter .mp4 files only
        mp4_files = [f for f in download_info.get('files', []) if f.lower().endswith('.mp4')]

        return jsonify({
            'success': True,
            'download_id': download_id,
            'files': mp4_files,
            'file_url' = f"https://testflask-ixf3.onrender.com/api/download/{download_id}/files/{mp4_files[0]}"
        })

    except Exception as e:
        app.logger.error(f"Download start error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/status/<download_id>', methods=['GET'])
def get_download_status(download_id):
    """Get download status"""
    if download_id not in active_downloads:
        return jsonify({'error': 'Download ID not found'}), 404
    
    return jsonify({
        'success': True,
        'download': active_downloads[download_id]
    })


@app.route('/api/downloads', methods=['GET'])
def list_downloads():
    """List all downloads with optional filtering"""
    status_filter = request.args.get('status')
    limit = request.args.get('limit', type=int)
    
    downloads = dict(active_downloads)
    
    if status_filter:
        downloads = {k: v for k, v in downloads.items() 
                    if v['status'] == status_filter}
    
    # Sort by creation time (newest first)
    sorted_downloads = dict(sorted(downloads.items(), 
                                  key=lambda x: x[1]['created_at'], 
                                  reverse=True))
    
    if limit:
        sorted_downloads = dict(list(sorted_downloads.items())[:limit])
    
    return jsonify({
        'success': True,
        'downloads': sorted_downloads,
        'total': len(sorted_downloads)
    })


@app.route('/api/download/<download_id>/files/<filename>', methods=['GET'])
def download_file(download_id, filename):
    """Download a specific file"""
    if download_id not in active_downloads:
        return jsonify({'error': 'Download ID not found'}), 404
    
    download_info = active_downloads[download_id]
    if download_info['status'] != 'completed':
        return jsonify({'error': 'Download not completed'}), 400
    
    file_path = Path(app.config['DOWNLOADS_DIR']) / download_id / filename
    
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        app.logger.error(f"File download error: {e}")
        return jsonify({'error': 'Failed to download file'}), 500


@app.route('/api/download/<download_id>/cancel', methods=['POST'])
def cancel_download(download_id):
    """Cancel a download"""
    if download_id not in active_downloads:
        return jsonify({'error': 'Download ID not found'}), 404
    
    download_info = active_downloads[download_id]
    if download_info['status'] not in ['queued', 'downloading']:
        return jsonify({'error': 'Cannot cancel download in current state'}), 400
    
    with download_lock:
        active_downloads[download_id]['status'] = 'cancelled'
        active_downloads[download_id]['cancelled_at'] = datetime.now().isoformat()
    
    return jsonify({
        'success': True,
        'message': 'Download cancelled'
    })


@app.route('/api/download/<download_id>', methods=['DELETE'])
def delete_download(download_id):
    """Delete a download and its files"""
    if download_id not in active_downloads:
        return jsonify({'error': 'Download ID not found'}), 404
    
    try:
        # Remove files
        download_dir = Path(app.config['DOWNLOADS_DIR']) / download_id
        if download_dir.exists():
            import shutil
            shutil.rmtree(download_dir)
        
        # Remove from active downloads
        with download_lock:
            del active_downloads[download_id]
        
        return jsonify({
            'success': True,
            'message': 'Download deleted'
        })
        
    except Exception as e:
        app.logger.error(f"Delete download error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get API statistics"""
    stats = {
        'total_downloads': len(active_downloads),
        'by_status': {},
        'active_count': 0,
        'disk_usage': 0
    }
    
    # Count by status
    for download in active_downloads.values():
        status = download['status']
        stats['by_status'][status] = stats['by_status'].get(status, 0) + 1
        if status in ['queued', 'downloading']:
            stats['active_count'] += 1
    
    # Calculate disk usage
    try:
        downloads_dir = Path(app.config['DOWNLOADS_DIR'])
        stats['disk_usage'] = sum(f.stat().st_size for f in downloads_dir.rglob('*') if f.is_file())
    except Exception:
        stats['disk_usage'] = 0
    
    return jsonify({
        'success': True,
        'stats': stats
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )