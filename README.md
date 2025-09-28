# Video Downloader API

A professional Flask-based REST API for downloading videos from various platforms including YouTube, Vimeo, Twitter, Instagram, TikTok, and many others. Built on top of `yt-dlp` with comprehensive error handling, logging, and management features.

## Features

### Core Functionality
- 🎥 **Multi-platform Support**: Download videos from 1000+ supported sites
- 🎵 **Audio-only Downloads**: Extract audio tracks in various formats
- 📱 **Playlist Support**: Download entire playlists or channels
- 🌍 **Subtitle Downloads**: Download subtitles in multiple languages
- 📊 **Format Selection**: Choose specific video quality and format
- 📋 **Video Information**: Extract metadata without downloading

### API Features
- 🚀 **RESTful API**: Clean, well-documented endpoints
- ⚡ **Async Downloads**: Non-blocking background downloads
- 📊 **Progress Tracking**: Real-time download status monitoring
- 🔄 **Concurrent Downloads**: Support for multiple simultaneous downloads
- 🗂️ **File Management**: Automatic cleanup and organization
- 📈 **Statistics**: Download analytics and usage metrics
- 🛡️ **Error Handling**: Comprehensive error reporting and logging

### Production Ready
- 🐳 **Docker Support**: Full containerization with Docker Compose
- 🔧 **Environment Configuration**: Flexible environment-based setup
- 📝 **Comprehensive Logging**: Detailed logging with rotation
- 🏥 **Health Checks**: Built-in health monitoring
- 🔒 **Security**: CORS support and request validation
- 📊 **Monitoring**: Built-in statistics and metrics

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd video-downloader-api
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env file with your configurations
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose up -d
   ```

4. **Access the API**
   ```
   http://localhost:5000/api/health
   ```

### Manual Installation

1. **Prerequisites**
   ```bash
   # Install FFmpeg (required)
   # Ubuntu/Debian
   sudo apt update && sudo apt install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows: Download from https://ffmpeg.org/download.html
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Copy your video_downloader.py**
   ```bash
   # Place your existing video_downloader.py in the root directory
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

## API Documentation

### Base URL
```
http://localhost:5000/api
```

### Endpoints

#### Health Check
```http
GET /api/health
```
**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "active_downloads": 2,
  "version": "1.0.0"
}
```

#### Get Video Information
```http
POST /api/info
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response:**
```json
{
  "success": true,
  "info": {
    "title": "Rick Astley - Never Gonna Give You Up",
    "duration": 212,
    "uploader": "Rick Astley",
    "view_count": 1234567890,
    "upload_date": "20091025",
    "formats": 25,
    "thumbnail": "https://...",
    "description": "The official video for..."
  }
}
```

#### Get Available Formats
```http
POST /api/formats
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

#### Start Download
```http
POST /api/download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "720p",
  "audio_only": false,
  "subtitles": ["en", "es"],
  "playlist": false
}
```

**Response:**
```json
{
  "success": true,
  "download_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Download started"
}
```

#### Check Download Status
```http
GET /api/status/{download_id}
```

**Response:**
```json
{
  "success": true,
  "download": {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "status": "completed",
    "created_at": "2024-01-01T12:00:00Z",
    "started_at": "2024-01-01T12:00:05Z",
    "completed_at": "2024-01-01T12:02:30Z",
    "options": {
      "quality": "720p",
      "audio_only": false
    },
    "files": ["Rick Astley - Never Gonna Give You Up.mp4"]
  }
}
```

#### List Downloads
```http
GET /api/downloads?status=completed&limit=10
```

#### Download File
```http
GET /api/download/{download_id}/files/{filename}
```

#### Cancel Download
```http
POST /api/download/{download_id}/cancel
```

#### Delete Download
```http
DELETE /api/download/{download_id}
```

#### Get Statistics
```http
GET /api/stats
```

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_downloads": 150,
    "by_status": {
      "completed": 120,
      "failed": 15,
      "downloading": 2
    },
    "active_count": 2,
    "disk_usage": 5368709120
  }
}
```

## Download Options

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `url` | string | Video URL (required) | - |
| `quality` | string | Video quality preference | `"best"` |
| `audio_only` | boolean | Download audio only | `false` |
| `subtitles` | array | Subtitle languages | `null` |
| `playlist` | boolean | Download entire playlist | `false` |
| `max_downloads` | integer | Max videos from playlist | `null` |

### Quality Options
- `"best"` - Best available quality
- `"worst"` - Worst available quality  
- `"720p"`, `"480p"`, `"360p"` - Specific resolutions
- `"bestvideo+bestaudio"` - Best video + best audio
- Custom format codes (use `/api/formats` to see available)

### Subtitle Languages
Common language codes: `en`, `es`, `fr`, `de`, `it`, `pt`, `ru`, `ja`, `ko`, `zh`

## Status Codes

| Status | Description |
|--------|-------------|
| `queued` | Download is queued |
| `downloading` | Download is in progress |
| `completed` | Download completed successfully |
| `failed` | Download failed |
| `cancelled` | Download was cancelled |

## Configuration

### Environment Variables

```bash
# Flask Configuration
FLASK_ENV=production
PORT=5000

# Download Configuration
DOWNLOADS_DIR=downloads
TEMP_DIR=temp
MAX_CONCURRENT_DOWNLOADS=3
CLEANUP_INTERVAL_HOURS=24

# Logging
LOG_LEVEL=INFO
```

### Docker Environment

The Docker setup includes:
- Automatic FFmpeg installation
- Volume mounts for persistent storage
- Health checks
- Non-root user execution
- Optimized Python environment

## Client Examples

### Python Client

```python
from client_example import VideoDownloaderClient

client = VideoDownloaderClient("http://localhost:5000")

# Get video info
info = client.get_video_info("https://youtube.com/watch?v=...")

# Start download
response = client.start_download(
    "https://youtube.com/watch?v=...",
    quality="720p",
    subtitles=["en"]
)

# Wait for completion
if response.get('success'):
    download_id = response['download_id']
    final_status = client.wait_for_download(download_id)
    
    if final_status['download']['status'] == 'completed':
        files = final_status['download']['files']
        # Download files locally
        for filename in files:
            client.download_file(download_id, filename, f"./{filename}")
```

### cURL Examples

```bash
# Health check
curl http://localhost:5000/api/health

# Get video info
curl -X POST http://localhost:5000/api/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# Start download
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "quality": "720p",
    "subtitles": ["en"]
  }'

# Check status
curl http://localhost:5000/api/status/DOWNLOAD_ID

# Download file
curl -o video.mp4 \
  http://localhost:5000/api/download/DOWNLOAD_ID/files/filename.mp4
```

## Supported Platforms

The API supports video downloads from 1000+ websites including:

- **Video Platforms**: YouTube, Vimeo, Dailymotion, Twitch
- **Social Media**: Twitter, Instagram, TikTok, Facebook
- **Educational**: Khan Academy, Coursera, edX
- **News**: CNN, BBC, NBC, ABC
- **Entertainment**: Netflix (some content), Hulu, Disney+
- **And many more...**

Full list available at: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md

## Monitoring and Logging

### Log Files
- `logs/api.log` - Application logs with rotation
- `downloads/*/download.log` - Individual download logs

### Metrics Available
- Total downloads count
- Downloads by status
- Active download count
- Disk usage statistics
- Download success/failure rates

### Health Checks
- `/api/health` endpoint for monitoring
- Docker health checks included
- Automatic unhealthy container restarts

## Error Handling

The API provides detailed error responses:

```json
{
  "error": "URL is required",
  "timestamp": "2024-01-01T12:00:00Z",
  "status_code": 400
}
```

Common error codes:
- `400` - Bad Request (missing/invalid parameters)
- `404` - Not Found (download ID or file not found)
- `429` - Too Many Requests (concurrent limit reached)
- `500` - Internal Server Error (processing error)

## Security Considerations

- Input validation on all endpoints
- File path sanitization
- Request size limits
- CORS configuration
- No direct file system access via API
- Automatic cleanup of old files

## Performance Optimization

- Background processing for downloads
- Concurrent download limiting
- File cleanup automation
- Efficient logging with rotation
- Docker multi-stage builds
- Gunicorn WSGI server

## Development

### Running Tests
```bash
pytest tests/
```

### Development Mode
```bash
export FLASK_DEBUG=True
python app.py
```

### Adding Features
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Troubleshooting

### Common Issues

**FFmpeg not found**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

**Permission errors**
```bash
# Fix directory permissions
sudo chown -R $USER:$USER downloads/ temp/ logs/
```

**Out of disk space**
```bash
# Check disk usage
df -h

# Clean old downloads
docker-compose exec video-downloader-api find /app/downloads -type f -mtime +7 -delete
```

**Memory issues**
```bash
# Reduce concurrent downloads
export MAX_CONCURRENT_DOWNLOADS=1
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

- Create an issue for bug reports
- Use discussions for questions
- Check existing issues before creating new ones

## Acknowledgments

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Powered by [Flask](https://flask.palletsprojects.com/)
- Containerized with [Docker](https://www.docker.com/)