#!/usr/bin/env python3
"""
Professional Video Downloader Script
Downloads videos from various sources using yt-dlp
Supports YouTube, Vimeo, Twitter, Instagram, TikTok, and many other platforms
"""

import os
import sys
import logging
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import subprocess

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp is not installed. Please install it using:")
    print("pip install yt-dlp")
    sys.exit(1)


class VideoDownloader:
    """Professional video downloader with comprehensive error handling and logging."""
    
    def __init__(self, output_dir: str = "downloads", quality: str = "best"):
        """
        Initialize the video downloader.
        
        Args:
            output_dir: Directory to save downloaded videos
            quality: Video quality preference (best, worst, or specific format)
        """
        # Get user's home directory and create Downloads folder
        home_dir = Path.home()
        local_downloads = home_dir / "Downloads" / "VideoDownloader"
        
        # If output_dir is default "downloads", use local Downloads folder
        if output_dir == "downloads":
            self.output_dir = local_downloads
        else:
            # If custom path provided, make it relative to user's Downloads
            self.output_dir = local_downloads / output_dir
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quality = quality
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration."""
        log_file = self.output_dir / "download.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract video information without downloading.
        
        Args:
            url: Video URL
            
        Returns:
            Dictionary containing video information or None if failed
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'formats': len(info.get('formats', [])),
                    'thumbnail': info.get('thumbnail', ''),
                    'description': info.get('description', '')[:200] + '...' if info.get('description') else ''
                }
        except Exception as e:
            self.logger.error(f"Failed to extract video info: {str(e)}")
            return None
    
    def get_download_options(self, url: str, audio_only: bool = False, 
                           subtitle_langs: Optional[list] = None) -> Dict[str, Any]:
        """
        Get yt-dlp download options.
        
        Args:
            url: Video URL
            audio_only: Download audio only
            subtitle_langs: List of subtitle languages to download
            
        Returns:
            Dictionary of yt-dlp options
        """
        # Create safe filename template with local path
        filename_template = str(self.output_dir / "%(title)s.%(ext)s")
        
        ydl_opts = {
            'outtmpl': filename_template,
            'format': 'bestaudio/best' if audio_only else self.quality,
            'writesubtitles': bool(subtitle_langs),
            'writeautomaticsub': bool(subtitle_langs),
            'subtitleslangs': subtitle_langs or [],
            'ignoreerrors': False,
            'no_warnings': False,
        }
        
        # Additional options for better compatibility
        if not audio_only:
            ydl_opts.update({
                'merge_output_format': 'mp4',
                'writeinfojson': True,
                'writethumbnail': True,
            })
        
        return ydl_opts
    
    def download_video(self, url: str, audio_only: bool = False, 
                      subtitle_langs: Optional[list] = None) -> bool:
        """
        Download video from given URL.
        
        Args:
            url: Video URL to download
            audio_only: Download only audio
            subtitle_langs: List of subtitle languages to download (e.g., ['en', 'es'])
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("Invalid URL format")
            
            self.logger.info(f"Starting download from: {url}")
            
            # Get video info first
            info = self.get_video_info(url)
            if info:
                self.logger.info(f"Video: {info['title']}")
                self.logger.info(f"Uploader: {info['uploader']}")
                self.logger.info(f"Duration: {info['duration']} seconds")
            
            # Download options
            ydl_opts = self.get_download_options(url, audio_only, subtitle_langs)
            
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            self.logger.info(f"Successfully downloaded: {url}")
            return True
            
        except yt_dlp.DownloadError as e:
            self.logger.error(f"Download error: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return False
    
    def download_playlist(self, url: str, max_downloads: Optional[int] = None) -> bool:
        """
        Download entire playlist or channel.
        
        Args:
            url: Playlist/Channel URL
            max_downloads: Maximum number of videos to download
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            ydl_opts = self.get_download_options(url)
            
            if max_downloads:
                ydl_opts['playlistend'] = max_downloads
            
            self.logger.info(f"Starting playlist download from: {url}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            self.logger.info(f"Successfully downloaded playlist: {url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Playlist download error: {str(e)}")
            return False
    
    def get_available_formats(self, url: str) -> Optional[list]:
        """
        Get all available formats for a video.
        
        Args:
            url: Video URL
            
        Returns:
            List of available formats or None if failed
        """
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                formats = info.get('formats', [])
                
                format_list = []
                for fmt in formats:
                    format_info = {
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext'),
                        'resolution': fmt.get('resolution'),
                        'filesize': fmt.get('filesize'),
                        'fps': fmt.get('fps'),
                        'vcodec': fmt.get('vcodec'),
                        'acodec': fmt.get('acodec'),
                    }
                    format_list.append(format_info)
                
                return format_list
                
        except Exception as e:
            self.logger.error(f"Failed to get formats: {str(e)}")
            return None


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: FFmpeg not found. Some format conversions may not work.")
        print("Install FFmpeg from: https://ffmpeg.org/download.html")


def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(
        description="Professional video downloader supporting multiple platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python video_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
  python video_downloader.py "https://vimeo.com/123456789" --audio-only
  python video_downloader.py "PLAYLIST_URL" --playlist --max-downloads 5
  python video_downloader.py "VIDEO_URL" --quality "720p" --subtitles en es
  python video_downloader.py "VIDEO_URL" --info-only
        """
    )
    
    parser.add_argument('url', help='Video URL to download')
    parser.add_argument('-o', '--output', default='downloads', 
                       help='Output directory (default: ~/Downloads/VideoDownloader)')
    parser.add_argument('-q', '--quality', default='best',
                       help='Video quality (best, worst, 720p, 480p, etc.)')
    parser.add_argument('--audio-only', action='store_true',
                       help='Download audio only')
    parser.add_argument('--playlist', action='store_true',
                       help='Download entire playlist')
    parser.add_argument('--max-downloads', type=int,
                       help='Maximum number of videos to download from playlist')
    parser.add_argument('--subtitles', nargs='+',
                       help='Subtitle languages to download (e.g., en es fr)')
    parser.add_argument('--info-only', action='store_true',
                       help='Show video information only, do not download')
    parser.add_argument('--formats', action='store_true',
                       help='List available formats for the video')
    
    args = parser.parse_args()
    
    # Check dependencies
    check_dependencies()
    
    # Initialize downloader
    downloader = VideoDownloader(args.output, args.quality)
    
    # Print download location for user reference
    print(f"Download location: {downloader.output_dir}")
    
    if args.info_only:
        info = downloader.get_video_info(args.url)
        if info:
            print("\n" + "="*50)
            print("VIDEO INFORMATION")
            print("="*50)
            for key, value in info.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        else:
            print("Failed to retrieve video information")
        return
    
    if args.formats:
        formats = downloader.get_available_formats(args.url)
        if formats:
            print("\n" + "="*80)
            print("AVAILABLE FORMATS")
            print("="*80)
            print(f"{'ID':<10} {'Extension':<10} {'Resolution':<12} {'FPS':<5} {'Video Codec':<12} {'Audio Codec':<12}")
            print("-"*80)
            for fmt in formats:
                print(f"{fmt['format_id']:<10} {fmt['ext']:<10} {fmt['resolution'] or 'N/A':<12} "
                      f"{fmt['fps'] or 'N/A':<5} {fmt['vcodec'] or 'N/A':<12} {fmt['acodec'] or 'N/A':<12}")
        else:
            print("Failed to retrieve format information")
        return
    
    # Download video(s)
    success = False
    if args.playlist:
        success = downloader.download_playlist(args.url, args.max_downloads)
    else:
        success = downloader.download_video(args.url, args.audio_only, args.subtitles)
    
    if success:
        print(f"\n✅ Download completed successfully!")
        print(f"Files saved to: {downloader.output_dir}")
    else:
        print(f"\n❌ Download failed. Check the log file for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()