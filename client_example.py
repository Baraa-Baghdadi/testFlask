#!/usr/bin/env python3
"""
Video Downloader API Client Examples
This file demonstrates how to use the Video Downloader API
"""

import requests
import time
import json
from typing import Dict, Any, Optional


class VideoDownloaderClient:
    """Client for interacting with the Video Downloader API"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        Initialize the client
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        response = self.session.get(f"{self.base_url}/api/health")
        return response.json()
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information without downloading
        
        Args:
            url: Video URL
            
        Returns:
            Video information dictionary
        """
        response = self.session.post(
            f"{self.base_url}/api/info",
            json={"url": url}
        )
        return response.json()
    
    def get_video_formats(self, url: str) -> Dict[str, Any]:
        """
        Get available video formats
        
        Args:
            url: Video URL
            
        Returns:
            Available formats dictionary
        """
        response = self.session.post(
            f"{self.base_url}/api/formats",
            json={"url": url}
        )
        return response.json()
    
    def start_download(self, url: str, **options) -> Dict[str, Any]:
        """
        Start video download
        
        Args:
            url: Video URL
            **options: Download options (quality, audio_only, subtitles, etc.)
            
        Returns:
            Download initiation response
        """
        payload = {"url": url, **options}
        response = self.session.post(
            f"{self.base_url}/api/download",
            json=payload
        )
        return response.json()
    
    def get_download_status(self, download_id: str) -> Dict[str, Any]:
        """
        Get download status
        
        Args:
            download_id: Download ID
            
        Returns:
            Download status dictionary
        """
        response = self.session.get(f"{self.base_url}/api/status/{download_id}")
        return response.json()
    
    def list_downloads(self, status: Optional[str] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        List all downloads
        
        Args:
            status: Filter by status (optional)
            limit: Limit number of results (optional)
            
        Returns:
            Downloads list dictionary
        """
        params = {}
        if status:
            params['status'] = status
        if limit:
            params['limit'] = limit
        
        response = self.session.get(f"{self.base_url}/api/downloads", params=params)
        return response.json()
    
    def download_file(self, download_id: str, filename: str, save_path: str) -> bool:
        """
        Download a specific file
        
        Args:
            download_id: Download ID
            filename: File name
            save_path: Local path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        response = self.session.get(
            f"{self.base_url}/api/download/{download_id}/files/{filename}",
            stream=True
        )
        
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    
    def cancel_download(self, download_id: str) -> Dict[str, Any]:
        """
        Cancel a download
        
        Args:
            download_id: Download ID
            
        Returns:
            Cancellation response
        """
        response = self.session.post(f"{self.base_url}/api/download/{download_id}/cancel")
        return response.json()
    
    def delete_download(self, download_id: str) -> Dict[str, Any]:
        """
        Delete a download and its files
        
        Args:
            download_id: Download ID
            
        Returns:
            Deletion response
        """
        response = self.session.delete(f"{self.base_url}/api/download/{download_id}")
        return response.json()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get API statistics"""
        response = self.session.get(f"{self.base_url}/api/stats")
        return response.json()
    
    def wait_for_download(self, download_id: str, check_interval: int = 5, timeout: int = 3600) -> Dict[str, Any]:
        """
        Wait for download to complete
        
        Args:
            download_id: Download ID
            check_interval: Seconds between status checks
            timeout: Maximum time to wait in seconds
            
        Returns:
            Final download status
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_download_status(download_id)
            
            if not status.get('success'):
                return status
            
            download_status = status['download']['status']
            
            if download_status in ['completed', 'failed', 'cancelled']:
                return status
            
            time.sleep(check_interval)
        
        return {'error': 'Download timeout'}


def example_usage():
    """Example usage of the Video Downloader API client"""
    
    # Initialize client
    client = VideoDownloaderClient("http://localhost:5000")
    
    # Example video URL (replace with actual URL)
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print("🔍 Video Downloader API Client Examples\n")
    
    # 1. Health check
    print("1. Health Check:")
    try:
        health = client.health_check()
        print(f"   Status: {health.get('status')}")
        print(f"   Active downloads: {health.get('active_downloads')}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # 4. Start a download
    print("4. Start Download:")
    try:
        download_options = {
            "quality": "720p",
            "audio_only": False,
            "subtitles": ["en"]
        }
        
        download_response = client.start_download(video_url, **download_options)
        if download_response.get('success'):
            download_id = download_response['download_id']
            print(f"   Download started with ID: {download_id}")
            
            # 5. Monitor download progress
            print("5. Monitor Download Progress:")
            print("   Waiting for download to complete...")
            
            final_status = client.wait_for_download(download_id, check_interval=2, timeout=300)
            
            if final_status.get('success'):
                status = final_status['download']['status']
                print(f"   Download {status}")
                
                if status == 'completed':
                    files = final_status['download']['files']
                    print(f"   Downloaded {len(files)} files:")
                    for file in files:
                        print(f"     - {file}")
                    
                    # 6. Download the first file
                    if files:
                        print("\n6. Download File:")
                        first_file = files[0]
                        local_path = f"./downloaded_{first_file}"
                        
                        success = client.download_file(download_id, first_file, local_path)
                        if success:
                            print(f"   File downloaded to: {local_path}")
                        else:
                            print("   Failed to download file")
            else:
                print(f"   Error: {final_status.get('error')}")
        else:
            print(f"   Error: {download_response.get('error')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 7. List all downloads
    print("\n7. List Downloads:")
    try:
        downloads = client.list_downloads(limit=5)
        if downloads.get('success'):
            print(f"   Total downloads: {downloads['total']}")
            for download_id, download_info in downloads['downloads'].items():
                print(f"   - {download_id}: {download_info['status']}")
        else:
            print(f"   Error: {downloads.get('error')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 8. Get API statistics
    print("\n8. API Statistics:")
    try:
        stats = client.get_stats()
        if stats.get('success'):
            stats_info = stats['stats']
            print(f"   Total downloads: {stats_info['total_downloads']}")
            print(f"   Active downloads: {stats_info['active_count']}")
            print(f"   Disk usage: {stats_info['disk_usage']} bytes")
            print(f"   Downloads by status: {stats_info['by_status']}")
        else:
            print(f"   Error: {stats.get('error')}")
    except Exception as e:
        print(f"   Error: {e}")


def batch_download_example():
    """Example of downloading multiple videos"""
    
    client = VideoDownloaderClient("http://localhost:5000")
    
    # List of video URLs to download
    video_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        # Add more URLs as needed
    ]
    
    print("🔄 Batch Download Example\n")
    
    download_ids = []
    
    # Start all downloads
    for i, url in enumerate(video_urls):
        try:
            print(f"Starting download {i+1}/{len(video_urls)}: {url}")
            response = client.start_download(url, quality="720p")
            
            if response.get('success'):
                download_id = response['download_id']
                download_ids.append(download_id)
                print(f"  Started with ID: {download_id}")
            else:
                print(f"  Failed: {response.get('error')}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Monitor all downloads
    print(f"\nMonitoring {len(download_ids)} downloads...")
    completed = 0
    
    while completed < len(download_ids):
        time.sleep(5)
        completed = 0
        
        for download_id in download_ids:
            try:
                status = client.get_download_status(download_id)
                if status.get('success'):
                    download_status = status['download']['status']
                    if download_status in ['completed', 'failed', 'cancelled']:
                        completed += 1
            except Exception:
                completed += 1
        
        print(f"  Progress: {completed}/{len(download_ids)} completed")
    
    # Show final results
    print("\nFinal Results:")
    for download_id in download_ids:
        try:
            status = client.get_download_status(download_id)
            if status.get('success'):
                download_info = status['download']
                print(f"  {download_id}: {download_info['status']}")
                if download_info['status'] == 'completed':
                    print(f"    Files: {len(download_info['files'])}")
        except Exception as e:
            print(f"  {download_id}: Error - {e}")


def playlist_download_example():
    """Example of downloading a playlist"""
    
    client = VideoDownloaderClient("http://localhost:5000")
    
    # Example playlist URL
    playlist_url = "https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab"
    
    print("📝 Playlist Download Example\n")
    
    try:
        # Get playlist info first
        print("Getting playlist information...")
        info = client.get_video_info(playlist_url)
        
        if info.get('success'):
            playlist_info = info['info']
            print(f"Title: {playlist_info.get('title')}")
            print(f"Uploader: {playlist_info.get('uploader')}")
        
        # Start playlist download
        print("Starting playlist download...")
        response = client.start_download(
            playlist_url,
            playlist=True,
            max_downloads=5,  # Limit to first 5 videos
            quality="480p"
        )
        
        if response.get('success'):
            download_id = response['download_id']
            print(f"Playlist download started with ID: {download_id}")
            
            # Wait for completion
            final_status = client.wait_for_download(download_id, check_interval=10, timeout=1800)
            
            if final_status.get('success'):
                status = final_status['download']['status']
                print(f"Playlist download {status}")
                
                if status == 'completed':
                    files = final_status['download']['files']
                    print(f"Downloaded {len(files)} files from playlist")
            else:
                print(f"Error: {final_status.get('error')}")
        else:
            print(f"Failed to start download: {response.get('error')}")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("Choose an example to run:")
    print("1. Basic API usage")
    print("2. Batch download")
    print("3. Playlist download")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == "1":
        example_usage()
    elif choice == "2":
        batch_download_example()
    elif choice == "3":
        playlist_download_example()
    else:
        print("Invalid choice. Running basic example...")
        example_usage()
    
    # 2. Get video information
    print("2. Get Video Information:")
    try:
        info = client.get_video_info(video_url)
        if info.get('success'):
            video_info = info['info']
            print(f"   Title: {video_info.get('title')}")
            print(f"   Duration: {video_info.get('duration')} seconds")
            print(f"   Uploader: {video_info.get('uploader')}\n")
        else:
            print(f"   Error: {info.get('error')}\n")
    except Exception as e:
        print(f"   Error: {e}\n")
    
    # 3. Get available formats
    print("3. Get Available Formats:")
    try:
        formats = client.get_video_formats(video_url)
        if formats.get('success'):
            print(f"   Found {len(formats['formats'])} formats")
            for fmt in formats['formats'][:3]:  # Show first 3 formats
                print(f"   - {fmt.get('format_id')}: {fmt.get('ext')} {fmt.get('resolution')}")
            print()
        else:
            print(f"   Error: {formats.get('error')}\n")