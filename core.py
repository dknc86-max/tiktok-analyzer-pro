"""
Core processing module for TikTok Analyzer Pro.
Handles video download, transcription, normalization, and analysis.
"""

import os
import re
import sys
import yt_dlp
import warnings
from queue import Queue
from logger import get_logger

import config

# Import logger for this module
logger = get_logger("core")

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

warnings.filterwarnings("ignore")

try:
    from faster_whisper import WhisperModel
    USE_FASTER = True
except ImportError:
    USE_FASTER = False
    WhisperModel = None

try:
    import imageio_ffmpeg
    ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass


def download_audio(
    video_url: str,
    output_path: str,
    timeout: int = None,
    retries: int = None,
    nocheckcertificate: bool = None,
) -> None:
    """
    Download audio from a TikTok video URL.
    
    Args:
        video_url: TikTok video URL
        output_path: Where to save the audio file
        timeout: Connection timeout in seconds (uses config default if None)
        retries: Number of retry attempts (uses config default if None)
        nocheckcertificate: Whether to skip SSL certificate verification
    """
    timeout = timeout or config.DOWNLOAD_TIMEOUT
    retries = retries or config.DOWNLOAD_RETRIES
    nocheckcertificate = nocheckcertificate if nocheckcertificate is not None else config.DOWNLOAD_CHECK_CERTIFICATE
    
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "quiet": True,
        "socket_timeout": timeout,
        "retries": retries,
        "nocheckcertificate": nocheckcertificate,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


def get_video_entries(profile_url: str) -> list:
    """
    Extract video entries from a TikTok creator profile.
    
    Args:
        profile_url: TikTok profile URL
        
    Returns:
        List of video entries
    """
    ydl_opts = {
        "extract_flat": "in_playlist",
        "dump_single_json": True,
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(profile_url, download=False)
        return result.get("entries", [result])


def transcribe_audio(model, audio_path: str) -> str:
    """
    Transcribe audio file to text using Faster Whisper or standard Whisper.
    
    Args:
        model: Whisper model instance
        audio_path: Path to audio file
        
    Returns:
        Transcribed text
    """
    if USE_FASTER:
        segments, _ = model.transcribe(
            audio_path,
            language="en",
            beam_size=config.WHISPER_BEAM_SIZE,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=config.WHISPER_VAD_MIN_SILENCE_MS,
                speech_pad_ms=config.WHISPER_VAD_SPEECH_PAD_MS,
            ),
        )
        return " ".join(seg.text for seg in segments).strip()
    else:
        import whisper as _whisper
        result = model.transcribe(audio_path)
        return result.get("text", "").strip()


def get_device() -> str:
    """
    Detect available compute device for Whisper.
    
    Returns:
        Device type: 'cuda', 'mps', or 'cpu'
    """
    if config.WHISPER_DEVICE != "auto":
        return config.WHISPER_DEVICE
    
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def get_compute_type(device: str) -> str:
    """
    Get compute type based on device.
    
    Args:
        device: Device type ('cuda', 'mps', or 'cpu')
        
    Returns:
        Compute type: 'float16', 'int8', etc.
    """
    if config.WHISPER_COMPUTE_TYPE != "auto":
        return config.WHISPER_COMPUTE_TYPE
    
    return "float16" if device == "cuda" else "int8"


def load_whisper_model(model_name: str = None) -> tuple:
    """
    Load Whisper model for transcription.
    
    Args:
        model_name: Model name (uses config default if None)
        
    Returns:
        Tuple of (model, device)
    """
    model_name = model_name or config.WHISPER_MODEL
    
    if USE_FASTER:
        device = get_device()
        return WhisperModel(model_name, compute_type=get_compute_type(device)), device
    else:
        import whisper
        device = get_device()
        model = whisper.load_model(model_name, device=device)
        return model, device


def normalize_transcript(text: str) -> str:
    """
    Normalize transcript by fixing common Whisper speech-to-text errors.
    Particularly for peptides and compound names.
    
    Args:
        text: Raw transcript text
        
    Returns:
        Normalized transcript
    """
    replacements = [
        (r"\bpenny\s+a\s+lan\b", "Pinealon"),
        (r"\bpenny-a-lan\b", "Pinealon"),
        (r"\bepitale\s+on\b", "Epitalon"),
        (r"\bepitale\b", "Epitalon"),
        (r"\bepithalon\b", "Epitalon"),
        (r"\bfox\s+o\'?\s+four\b", "FOXO4-DRI"),
        (r"\bfox\s+o\s+four\b", "FOXO4-DRI"),
        (r"\bfoxo\s*4\b", "FOXO4-DRI"),
        (r"\bmotts?\s*-\s*c\b", "MOTS-c"),
        (r"\bmott\s+c\b", "MOTS-c"),
        (r"\bmat\s*-\s*c\b", "MOTS-c"),
        (r"\bmat\s+c\b", "MOTS-c"),
        (r"\bmatsui\b", "MOTS-c"),
        (r"\bmatsu\b", "MOTS-c"),
        (r"\bred\s*,?\s+f[u\*][c\*][k\*](?:ing)?\s+t(?:ide|ied)\b", "Retatrutide"),
        (r"\bred\s+and\b", "Retatrutide"),
        (r"\bred\s+end\b", "Retatrutide"),
        (r"\bhard\s+r\b", "Retatrutide"),
        (r"\bhard-art-art\b", "Retatrutide"),
        (r"\bhard-art\b", "Retatrutide"),
        (r"\bslnc\b", "Selank"),
        (r"\bs-l-n-c\b", "Selank"),
        (r"\bsalank\b", "Selank"),
        (r"\bthe\s+big\s+length\b", "Selank"),
        (r"\bc\s+max\b", "Semax"),
        (r"\bsermerallin\b", "Sermorelin"),
        (r"\bsermerall\b", "Sermorelin"),
        (r"\bsermerellin\b", "Sermorelin"),
        (r"\bsermorale\b", "Sermorelin"),
        (r"\bbpc\s*-\s*157\b", "BPC-157"),
        (r"\bbpc\s+157\b", "BPC-157"),
        (r"\bbpc157\b", "BPC-157"),
        (r"\btb\s*-\s*500\b", "TB-500"),
        (r"\btb\s+500\b", "TB-500"),
        (r"\btb500\b", "TB-500"),
        (r"\bghk\s*-\s*cu\b", "GHK-Cu"),
        (r"\bghk\s+cu\b", "GHK-Cu"),
        (r"\bghk-c\b", "GHK-Cu"),
        (r"\bghk\s+c\b", "GHK-Cu"),
        (r"\btessa\s+ipa\s+blend\b", "Tesamorelin / Ipamorelin Blend"),
        (r"\btessa\s+ipa\s+psych\b", "Tesamorelin / Ipamorelin cycle"),
        (r"\btessa\s+ipa\b", "Tesamorelin / Ipamorelin"),
        (r"\btessa\s+and\s+ipa\b", "Tesamorelin / Ipamorelin"),
        (r"\btess\s+and\s+ipa\b", "Tesamorelin / Ipamorelin"),
        (r"\btessa\s+morelana\b", "Tesamorelin"),
        (r"\bgrowth\s+hormones?\s+to\s+kreeti\s+gog\b", "growth hormone secretagogue"),
        (r"\bgrowth\s+hormones?\s+to\s+creati\s+gog\b", "growth hormone secretagogue"),
        (r"\bgrowth\s+hormones?\s+to\s+create\s+a\s+dog\b", "growth hormone secretagogue"),
        (r"\bmilano\s*-?\s*10\s+(?:too|2)\b", "Melanotan 2"),
        (r"\bmilano\s*-?\s*10\b", "Melanotan"),
        (r"\bin\s+clomophine\b", "enclomiphene"),
        (r"\bin\s+clomiphine\b", "enclomiphene"),
        (r"\bclomophine\b", "enclomiphene"),
        (r"\bclomiphine\b", "enclomiphene"),
        (r"\bfotitti\b", "Fo-Ti"),
        (r"\bdrop\s+the\s+zal\b", "drop the cortisol"),
        (r"\binfested\s+with\s+the\s+zal\b", "infested with the cortisol"),
        (r"\bthe\s+zal\b", "the cortisol"),
        (r"\bthe\s+big\s+bee\b", "the big brain"),
        (r"\bcrying\s+and\s+seed\s+on\s+half\s+to\b", "Trying and See You Don't Have To"),
        (r"\bthe\s+getter\s+stack\b", "the beginner stack"),
    ]
    normalized = text
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized


def classify_video(transcript: str, title: str = "") -> str:
    """
    Classify video content into categories based on keywords.
    
    Args:
        transcript: Video transcript text
        title: Video title (optional)
        
    Returns:
        Category string
    """
    normalized = normalize_transcript(transcript)
    t = normalized.lower()

    if len(normalized) < config.MIN_TRANSCRIPT_LENGTH:
        return "general_advice"

    if any(j in t for j in config.JUNK_INDICATORS):
        return "general_advice"

    if any(
        x in t
        for x in [
            "peptide",
            "bpc",
            "tb500",
            "ghk",
            "ss31",
            "mots-c",
            "mott c",
            "matsu",
            "matsui",
            "mat-c",
            "sermerall",
            "sermorelin",
            "epitale",
            "epitalon",
            "foxo",
            "selank",
            "semax",
            "kpv",
            "dsip",
            "d-sip",
            "melanotan",
            "milano",
            "thymosin",
            "pinealon",
            "growth hormone",
        ]
    ):
        if any(x in t for x in ["stack", "protocol", "phase", "experiment"]):
            return "peptide_protocol"
        return "peptide_info"

    if any(
        x in t
        for x in [
            "retitatide",
            "retatrutide",
            "reta",
            "red end",
            "red and",
            "hard r",
            "hard-art",
            "glp",
            "semaglutide",
            "tirzepatide",
        ]
    ):
        return "glp1_fat_loss"

    if any(
        x in t
        for x in [
            "testosterone",
            "trt",
            "hormones",
            "test is at",
            "estrogen",
            "clomiphine",
            "enclomiphene",
        ]
    ):
        return "hormones"

    if any(
        x in t
        for x in [
            "mitochondria",
            "cellular energy",
            "cellular biology",
            "ampk",
            "miostat",
        ]
    ):
        return "mitochondria"

    if any(
        x in t
        for x in [
            "intermittent fasting",
            "fasting",
            "calorie",
            "protein",
            "diet",
            "eating",
            "macros",
            "surplus",
        ]
    ):
        return "nutrition"

    if any(
        x in t
        for x in [
            "cortisol",
            "sleep",
            "recovery",
            "dopamine",
            "mental health",
            "stress",
            "brain",
        ]
    ):
        return "wellness_mindset"

    if any(
        x in t
        for x in [
            "workout",
            "gym",
            "muscle",
            "training",
            "cardio",
            "exercise",
            "physique",
        ]
    ):
        return "fitness"

    if any(x in t for x in ["fda", "legalized", "industry", "western medicine", "doctors"]):
        return "industry_news"

    return "general_advice"


def extract_gemini_bullets(transcript: str, category: str, api_key: str = None) -> list:
    """
    Extract bullet points using Google Gemini API.
    
    Args:
        transcript: Video transcript
        category: Content category
        api_key: Gemini API key (uses config if None)
        
    Returns:
        List of bullet point strings or None if API unavailable
    """
    if not HAS_GENAI:
        return None
    
    api_key = api_key or config.GEMINI_API_KEY
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
        cleaned_transcript = normalize_transcript(transcript)

        prompt = f"""You are an expert health and peptide protocol research analyst. Your job is to extract highly accurate, specific, and actionable summaries from transcripts of short video clips.

Here is an example of a high-quality manual summary:
Transcript: "Today's episode is the best things I've learned from my own experiments on myself and my own research for anybody who wants to get more out of their peptides or is thinking about starting..."
Category: Peptide Protocol
Summary:
- **Compounds mentioned**: BPC-157, TB-500
- **Systemic Inflammation**: He notes that systemic inflammation is the killer of all peptides and blocks their signals.
- **Loading Phase Recommendation**: Recommends starting with BPC-157 and TB-500 to clear inflammation so the body can receive other peptide signals.
- **Collagen co-factor**: Emphasizes that you must take a collagen supplement alongside these peptides.

Now, analyze the following video transcript and category, and generate a similar, high-quality, structured summary. Do not include conversational filler, meta-text, or intros (like "This video discusses...").

Transcript: "{cleaned_transcript}"
Category: {category}

Return the summary as a list of bullet points starting directly with `- `. Make each bullet point concise and clear. If a compound has a specific dose mentioned, make sure to include it.
"""
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
        )

        bullets = []
        for line in response.text.strip().split("\n"):
            line = line.strip()
            if line.startswith("-"):
                bullets.append(line.lstrip("- ").strip())
            elif line:
                bullets.append(line)
        return bullets
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return None


def extract_fallback_bullets(transcript: str, category: str) -> list:
    """
    Extract bullet points using heuristic pattern matching (offline fallback).
    
    Args:
        transcript: Video transcript
        category: Content category
        
    Returns:
        List of bullet point strings
    """
    normalized = normalize_transcript(transcript)
    sentences = re.split(r"(?<=[.!?])\s+", normalized.strip())

    clean_sentences = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        lower_sent = sent.lower()
        if any(re.search(pat, lower_sent) for pat in config.FILLER_PATTERNS):
            continue
        clean_sentences.append(sent)

    compounds_found = []
    for c in config.COMPOUNDS:
        if re.search(r"\b" + re.escape(c.lower()) + r"\b", normalized.lower()):
            compounds_found.append(c)

    bullets = []

    if compounds_found:
        bullets.append(f"**Compounds mentioned**: {', '.join(compounds_found)}")

    protocol_sentences = []
    seen = set()

    for sent in clean_sentences:
        sent_lower = sent.lower()
        has_compound = any(
            re.search(r"\b" + re.escape(c.lower()) + r"\b", sent_lower)
            for c in config.COMPOUNDS
        )
        has_action = any(
            re.search(r"\b" + re.escape(act) + r"\b", sent_lower)
            for act in config.ACTION_KEYWORDS
        )

        if has_compound and has_action:
            if sent_lower[:40] not in seen:
                seen.add(sent_lower[:40])
                protocol_sentences.append(sent)

    bullets.extend(protocol_sentences[:4])

    if len(bullets) < 4:
        for sent in clean_sentences:
            sent_lower = sent.lower()
            if any(re.search(pat, sent_lower) for pat in config.ADVICE_KEYWORDS):
                if sent_lower[:40] not in seen:
                    seen.add(sent_lower[:40])
                    bullets.append(sent)
                    if len(bullets) >= 5:
                        break

    if len(bullets) < 2:
        for sent in clean_sentences[:3]:
            sent_lower = sent.lower()
            if sent_lower[:40] not in seen:
                seen.add(sent_lower[:40])
                bullets.append(sent)

    return bullets


def generate_topic_summary(transcript: str) -> str:
    """
    Generate a short topic summary from transcript.
    
    Args:
        transcript: Video transcript
        
    Returns:
        Short topic summary (max 120 chars)
    """
    sentences = re.split(r"(?<=[.!?])\s+", transcript)

    best = None
    for sent in sentences[:5]:
        lower = sent.lower().strip()
        if any(lower.startswith(s) for s in config.SKIP_INTROS):
            continue
        if len(sent.strip()) > 20:
            best = sent.strip()
            break

    if not best:
        best = sentences[0].strip() if sentences else "General discussion"

    if len(best) > 120:
        best = best[:117] + "..."

    return best


def extract_suggestions(transcript: str, category: str, api_key: str = None) -> tuple:
    """
    Extract topic and bullet point suggestions from transcript.
    Uses Gemini if available, falls back to heuristic extraction.
    
    Args:
        transcript: Video transcript
        category: Content category
        api_key: Optional Gemini API key override
        
    Returns:
        Tuple of (topic_summary, bullet_list)
    """
    topic = generate_topic_summary(transcript)

    gemini_bullets = extract_gemini_bullets(transcript, category, api_key)
    if gemini_bullets:
        return topic, gemini_bullets

    return topic, extract_fallback_bullets(transcript, category)


def extract_video_id(url: str) -> str:
    """
    Extract video ID from TikTok URL.
    
    Args:
        url: TikTok video URL
        
    Returns:
        Video ID string or None
    """
    if not url:
        return None
    match = re.search(r"/video/(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"\b\d{18,22}\b", url)
    if match:
        return match.group(0)
    return None


def load_transcript_cache(filepath: str) -> dict:
    """
    Load transcript cache from file.
    
    Args:
        filepath: Path to transcripts markdown file
        
    Returns:
        Dictionary mapping video IDs to transcripts
    """
    cache = {}
    if not os.path.exists(filepath):
        return cache
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        blocks = content.split("\n## ")[1:]
        for block in blocks:
            lines = block.strip().split("\n")
            if not lines:
                continue
            title = lines[0].strip()
            url = ""
            transcript_lines = []
            for line in lines[1:]:
                if line.startswith("URL:"):
                    url = line.replace("URL:", "").strip()
                elif line.strip():
                    transcript_lines.append(line.strip())

            transcript = " ".join(transcript_lines)
            transcript = re.sub(r"\s+", " ", transcript).strip()

            video_id = extract_video_id(url)
            if video_id:
                cache[video_id] = transcript
    except Exception as e:
        logger.error(f"Error loading transcript cache: {e}")
    return cache


def append_to_transcripts_file(filepath: str, title: str, url: str, transcript: str) -> None:
    """
    Append a transcript entry to the shared transcripts file.
    
    Args:
        filepath: Path to transcripts markdown file
        title: Video title
        url: Video URL
        transcript: Video transcript
    """
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n## {title}\nURL: {url}\n\n{transcript}\n\n")
    except Exception as e:
        logger.error(f"Error appending to transcripts: {e}")
