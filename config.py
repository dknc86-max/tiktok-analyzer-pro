"""
Configuration management for TikTok Analyzer Pro.
Centralizes all settings and environment variables.
"""

import os
from pathlib import Path

# ============================================================================
# Environment & Paths
# ============================================================================
PROJECT_ROOT = Path(__file__).parent
RESULTS_DIR = PROJECT_ROOT / "results"
CACHE_DIR = PROJECT_ROOT / "cache"
TRANSCRIPTS_FILE = PROJECT_ROOT / "transcripts.md"

# Create directories if they don't exist
RESULTS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ============================================================================
# API Configuration
# ============================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Rate limiting for Gemini API (free tier limit)
GEMINI_MAX_REQUESTS_PER_MINUTE = int(os.environ.get("GEMINI_MAX_RPM", "12"))
GEMINI_REQUEST_TIMEOUT = int(os.environ.get("GEMINI_TIMEOUT", "30"))

# ============================================================================
# Whisper Configuration
# ============================================================================
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small.en")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "auto")  # auto, cuda, mps, cpu
WHISPER_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "auto")  # auto, float16, int8

# Whisper VAD (Voice Activity Detection) parameters
WHISPER_VAD_MIN_SILENCE_MS = int(os.environ.get("WHISPER_VAD_MIN_SILENCE_MS", "500"))
WHISPER_VAD_SPEECH_PAD_MS = int(os.environ.get("WHISPER_VAD_SPEECH_PAD_MS", "200"))
WHISPER_BEAM_SIZE = int(os.environ.get("WHISPER_BEAM_SIZE", "3"))

# ============================================================================
# Video Download Configuration
# ============================================================================
DOWNLOAD_TIMEOUT = int(os.environ.get("DOWNLOAD_TIMEOUT", "15"))
DOWNLOAD_RETRIES = int(os.environ.get("DOWNLOAD_RETRIES", "3"))
DOWNLOAD_CHECK_CERTIFICATE = os.environ.get("DOWNLOAD_CHECK_CERTIFICATE", "true").lower() == "true"

# ============================================================================
# Flask Web App Configuration
# ============================================================================
FLASK_HOST = os.environ.get("FLASK_HOST", "localhost")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5001"))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
FLASK_ENV = os.environ.get("FLASK_ENV", "production")

# ============================================================================
# Processing Configuration
# ============================================================================
# Maximum videos to process per profile
MAX_VIDEOS_PER_PROFILE = int(os.environ.get("MAX_VIDEOS_PER_PROFILE", "0"))  # 0 = unlimited

# Minimum transcript length to be considered "substantive"
MIN_TRANSCRIPT_LENGTH = int(os.environ.get("MIN_TRANSCRIPT_LENGTH", "200"))

# ============================================================================
# Logging Configuration
# ============================================================================
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = os.environ.get("LOG_FILE", "tiktok_analyzer.log")

# ============================================================================
# Content Classification Keywords
# ============================================================================
JUNK_INDICATORS = [
    "i'm gonna be right back",
    "they don't break on their ass",
    "from a man named",
    "i love it! i got this feeling",
    "blame, you're a little",
    "manausages",
    "trying and see you don't have to",
]

FILLER_PATTERNS = [
    r"^today's\s+episode",
    r"^welcome\s+back",
    r"^if\s+you\s+don't\s+know",
    r"^quick\s+recap",
    r"^recap\s+if\s+you",
    r"^in\s+this\s+video",
    r"^i'm\s+constantly\s+researching",
    r"^i\s+never\s+let\s+comments",
    r"under\s+my\s+skin",
    r"dumb\s+shit",
    r"ass\s+doctors",
    r"wasting\s+my\s+money",
    r"this\s+is\s+what\s+i've\s+been\s+trying",
    r"caught\s+dead\s+going\s+for\s+a",
    r"sooner\s+be\s+caught",
    r"why\s+are\s+you\s+doing\s+this",
    r"you\s+guys\s+know",
    r"i\s+figured\s+it\s+out",
    r"i\s+got\s+some\s+good",
    r"it's\s+happening",
    r"i'm\s+gonna\s+be\s+right\s+back",
]

SKIP_INTROS = [
    "welcome back",
    "if you don't know me",
    "you guys know",
    "i got some good",
    "guys,",
    "it's happening",
    "i figured it out",
    "today's episode",
]

COMPOUNDS = [
    "BPC-157",
    "TB-500",
    "GHK-Cu",
    "KPV",
    "Pinealon",
    "Epitalon",
    "FOXO4-DRI",
    "Selank",
    "Semax",
    "MOTS-c",
    "Retatrutide",
    "Tirzepatide",
    "Semaglutide",
    "Tesamorelin",
    "Ipamorelin",
    "TRT",
    "Testosterone",
    "Glutathione",
    "NAD+",
    "Sermorelin",
    "Dihexa",
    "DSIP",
    "Melanotan",
]

ACTION_KEYWORDS = [
    "take",
    "taking",
    "inject",
    "injection",
    "subq",
    "dose",
    "dosing",
    "mg",
    "mcg",
    "milligram",
    "microgram",
    "stack",
    "stacking",
    "paired",
    "combine",
    "combining",
    "morning",
    "night",
    "bed",
    "daily",
    "cycle",
    "week",
    "month",
    "fasting",
    "empty stomach",
]

ADVICE_KEYWORDS = [
    "should",
    "need",
    "must",
    "recommend",
    "important",
    "crucial",
    "key",
    "tip",
    "advice",
]
