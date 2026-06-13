# Troubleshooting Guide

## Common Issues & Solutions

### Installation & Setup

#### 1. FFmpeg Not Found
**Error**: `imageio_ffmpeg.source: ffmpeg not found`

**Solution**:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
# Or use Chocolatey: choco install ffmpeg

# Verify installation
ffmpeg -version
```

#### 2. Virtual Environment Issues
**Error**: `pip: command not found` or module import errors

**Solution**:
```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

#### 3. Python Version Incompatibility
**Error**: `SyntaxError` or `UnsupportedFeature`

**Solution**:
```bash
# Check Python version (must be 3.8+)
python --version

# Update to Python 3.10+
# - macOS: brew install python@3.11
# - Ubuntu: sudo apt-get install python3.11
# - Windows: Download from python.org
```

---

### Transcription Issues

#### 4. Whisper Model Download Fails
**Error**: `Connection timeout` or `Model download failed`

**Solution**:
```bash
# Use smaller model initially
# In config.py or .env:
WHISPER_MODEL=tiny.en

# Or manually download model:
python -c "from faster_whisper import WhisperModel; WhisperModel('small.en')"

# Try with proxy if behind firewall
export HTTP_PROXY=http://proxy:port
```

#### 5. Out of Memory During Transcription
**Error**: `CUDA out of memory` or `MemoryError`

**Solution**:
```bash
# Option 1: Use smaller model
WHISPER_MODEL=tiny.en

# Option 2: Use CPU instead of GPU
WHISPER_DEVICE=cpu

# Option 3: Use lower compute precision
WHISPER_COMPUTE_TYPE=int8

# Option 4: Process fewer videos
MAX_VIDEOS_PER_PROFILE=50
```

#### 6. Poor Transcription Quality
**Issue**: Many transcription errors, especially for domain-specific terms

**Solution**:
```bash
# Increase beam size for better accuracy (slower)
WHISPER_BEAM_SIZE=5

# Use larger model
WHISPER_MODEL=base.en
# or
WHISPER_MODEL=small.en

# Enable VAD for better silence detection
WHISPER_VAD_MIN_SILENCE_MS=300
```

---

### API & Network Issues

#### 7. Gemini API Key Not Working
**Error**: `API key invalid` or `Authentication failed`

**Solution**:
```bash
# Verify API key format
# Should be alphanumeric, ~40 characters

# Get new key from Google AI Studio:
# https://aistudio.google.com/

# Set in .env:
GEMINI_API_KEY=your-key-here

# Test connection:
python -c "from core import extract_gemini_bullets; print('OK')"
```

#### 8. Rate Limiting / Too Many Requests
**Error**: `Rate limit exceeded` or `429 Too Many Requests`

**Solution**:
```bash
# Reduce requests per minute (free tier = 12 RPM)
GEMINI_MAX_RPM=10

# Add delay between requests
import time
time.sleep(5)  # Wait 5 seconds

# Use fallback summarization (no API calls)
# In core.py: extract_fallback_bullets() doesn't use API
```

#### 9. TikTok Video Download Fails
**Error**: `yt-dlp: Unable to extract video` or `Video unavailable`

**Solution**:
```bash
# Update yt-dlp (frequently needs updates)
pip install --upgrade yt-dlp

# Increase timeout
DOWNLOAD_TIMEOUT=30

# More retries
DOWNLOAD_RETRIES=5

# Disable certificate check (if behind proxy)
DOWNLOAD_CHECK_CERTIFICATE=false

# Check if creator profile is public
# Some creators may have private profiles

# Try specific video URL instead of profile:
python analyze_tiktok.py https://www.tiktok.com/@creator/video/123456
```

#### 10. Network Timeout
**Error**: `Connection timeout` or `Socket timeout`

**Solution**:
```bash
# Increase timeout values
DOWNLOAD_TIMEOUT=30
GEMINI_TIMEOUT=60

# Check internet connection:
ping google.com

# Try using a proxy:
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=https://proxy:port

# Disable SSL verification (last resort):
DOWNLOAD_CHECK_CERTIFICATE=false
```

---

### Web App Issues

#### 11. Flask Server Won't Start
**Error**: `Address already in use` or `Port X already in use`

**Solution**:
```bash
# Change port in .env:
FLASK_PORT=8000

# Or kill process using the port:
# macOS/Linux
lsof -ti:5001 | xargs kill -9

# Windows
netstat -ano | findstr :5001
taskkill /PID <PID> /F
```

#### 12. Web UI Not Responsive
**Issue**: Dashboard loads but is slow or unresponsive

**Solution**:
```bash
# Enable debug mode to see errors:
FLASK_DEBUG=true

# Check browser console (F12 → Console tab)

# Clear browser cache:
# Ctrl+Shift+Delete (Windows) or Cmd+Shift+Delete (Mac)

# Try different browser (Chrome, Firefox, Safari)

# Check if JavaScript is enabled
```

#### 13. Can't Find Results After Analysis
**Error**: `Results not found` or `No results for username`

**Solution**:
```bash
# Check results directory exists:
ls -la results/  # or dir results/ on Windows

# Verify analysis completed:
# Look for logs: tail -f logs/tiktok_analyzer.log

# Check file permissions:
chmod 755 results/  # macOS/Linux

# Ensure enough disk space:
df -h  # macOS/Linux
dir C:\  # Windows
```

---

### Performance Issues

#### 14. Analysis Takes Too Long
**Issue**: Processing is very slow, especially for large profiles

**Solution**:
```bash
# Use GPU acceleration (if available):
WHISPER_DEVICE=cuda

# Use faster model:
WHISPER_MODEL=tiny.en

# Limit videos processed:
MAX_VIDEOS_PER_PROFILE=50

# Run as background job instead of waiting

# Check system resources:
# macOS: top
# Linux: htop
# Windows: Task Manager
```

#### 15. High Memory Usage
**Error**: Application keeps growing in memory, crashes

**Solution**:
```bash
# Process videos in batches:
MAX_VIDEOS_PER_PROFILE=20

# Clear cache periodically:
rm -rf cache/*

# Reduce model size:
WHISPER_MODEL=tiny.en

# Monitor memory:
# macOS/Linux: watch -n 1 'ps aux | grep python'
# Windows: Task Manager → Performance tab
```

---

### Testing Issues

#### 16. Tests Fail or Won't Run
**Error**: `pytest: command not found` or tests fail

**Solution**:
```bash
# Install test dependencies:
pip install -r requirements-dev.txt

# Run tests with verbose output:
pytest -v

# Run specific test:
pytest tests/test_core.py::TestNormalizeTranscript -v

# Run with coverage report:
pytest --cov=. tests/
```

#### 17. Mock/Patch Issues in Tests
**Error**: `Cannot patch module` or mock not working

**Solution**:
```python
# Ensure correct import path
from unittest.mock import patch, Mock

# Patch where it's used, not where it's defined
@patch('core.genai.Client')  # ✓ Correct
@patch('google.genai.Client')  # ✗ Wrong

# Use context manager for clarity:
with patch('core.yt_dlp.YoutubeDL') as mock_ydl:
    # Test code
    pass
```

---

### Logging & Debugging

#### 18. No Logs or Logs Not Helpful
**Solution**:
```bash
# Change log level for more verbosity:
LOG_LEVEL=DEBUG

# Check log file:
tail -f logs/tiktok_analyzer.log

# Tail with filtering:
grep ERROR logs/tiktok_analyzer.log

# Enable Flask debug mode:
FLASK_DEBUG=true
```

#### 19. Debug Mode Not Working
**Solution**:
```bash
# Ensure env var is set:
export FLASK_DEBUG=true

# Or set directly in config:
# config.py: FLASK_DEBUG = True

# Restart Flask server completely:
# Kill all python processes and restart
```

---

## Getting Help

1. **Check Logs**: Look in `logs/tiktok_analyzer.log` for detailed error messages
2. **Search Issues**: https://github.com/dknc86-max/tiktok-analyzer-pro/issues
3. **Review Configuration**: Verify `.env` settings match your needs
4. **Test Individually**: Test each component (download, transcribe, summarize) separately
5. **Check Dependencies**: `pip list` and verify versions match `requirements.txt`

## Reporting Issues

If you can't solve the problem:

1. Check this troubleshooting guide
2. Search existing GitHub issues
3. Create a new issue with:
   - Error message and stack trace
   - Steps to reproduce
   - Your environment (OS, Python version, etc.)
   - Configuration settings (without secrets)
   - Relevant logs from `logs/tiktok_analyzer.log`

---

**Last Updated**: 2026-06-13
