import os
import re
import sys
import json
import time
import hashlib
import yt_dlp
import warnings
from queue import Queue

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

COMPOUNDS = [
    'BPC-157', 'TB-500', 'GHK-Cu', 'KPV', 'Pinealon', 'Epitalon',
    'FOXO4-DRI', 'Selank', 'Semax', 'MOTS-c', 'Retatrutide', 'Tirzepatide',
    'Semaglutide', 'Tesamorelin', 'Ipamorelin', 'TRT', 'Testosterone',
    'Glutathione', 'NAD+', 'Sermorelin', 'Dihexa', 'DSIP', 'Melanotan'
]

INTERACTION_WARNINGS = [
    (['Melanotan', 'Retatrutide'], "Melanotan + Retatrutide: both may affect appetite/metabolism; monitor closely."),
    (['DSIP', 'Stimulants'], "DSIP + stimulants: may interfere with sleep architecture."),
    (['TB-500', 'BPC-157'], "TB-500 + BPC-157: commonly stacked; no known adverse interaction."),
    (['Semaglutide', 'Tirzepatide'], "Semaglutide + Tirzepatide: dual GLP-1 use increases GI side effect risk."),
    (['MOTS-c', 'Metformin'], "MOTS-c + Metformin: both activate AMPK; monitor for hypoglycemia."),
    (['Sermorelin', 'Ipamorelin'], "Sermorelin + Ipamorelin: standard GHRP/GHRH stack; generally synergistic."),
]


def download_audio(video_url, output_path, timeout=15, retries=5, nocheckcertificate=True):
    for attempt in range(retries):
        try:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'quiet': True,
                'socket_timeout': timeout,
                'retries': 3 if attempt < retries - 1 else 5,
                'nocheckcertificate': nocheckcertificate,
                'continuedl': True,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            return
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


def get_video_entries(profile_url):
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'dump_single_json': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(profile_url, download=False)
        return result.get('entries', [result])


def transcribe_audio(model, audio_path, return_segments=False, language=None):
    kwargs = dict(
        beam_size=3,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
    )
    if language:
        kwargs['language'] = language

    if USE_FASTER:
        segments, info = model.transcribe(audio_path, **kwargs)
        segments = list(segments)
        text = " ".join(seg.text for seg in segments).strip()
        if return_segments:
            return text, [(seg.start, seg.end, seg.text.strip(), getattr(seg, 'avg_logprob', 0.0)) for seg in segments], info
        return text
    else:
        import whisper as _whisper
        result = model.transcribe(audio_path, language=language)
        text = result.get("text", "").strip()
        if return_segments:
            segs = []
            for s in result.get("segments", []):
                segs.append((s.get('start', 0), s.get('end', 0), s.get('text', '').strip(), s.get('avg_logprob', 0.0)))
            return text, segs, None
        return text


def get_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def get_compute_type(device):
    return "float16" if device == "cuda" else "int8"


def load_whisper_model(model_name="small.en", device=None):
    if device is None:
        device = get_device()
    if USE_FASTER:
        return WhisperModel(model_name, compute_type=get_compute_type(device)), device
    else:
        import whisper
        model = whisper.load_model(model_name, device=device)
        return model, device


def video_hash(url, title=""):
    raw = f"{url}|{title}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def normalize_transcript(text):
    replacements = [
        (r'\bpenny\s+a\s+lan\b', 'Pinealon'),
        (r'\bpenny-a-lan\b', 'Pinealon'),
        (r'\bepitale\s+on\b', 'Epitalon'),
        (r'\bepitale\b', 'Epitalon'),
        (r'\bepithalon\b', 'Epitalon'),
        (r'\bfox\s+o\'?\s+four\b', 'FOXO4-DRI'),
        (r'\bfox\s+o\s+four\b', 'FOXO4-DRI'),
        (r'\bfoxo\s*4\b', 'FOXO4-DRI'),
        (r'\bmotts?\s*-\s*c\b', 'MOTS-c'),
        (r'\bmott\s+c\b', 'MOTS-c'),
        (r'\bmat\s*-\s*c\b', 'MOTS-c'),
        (r'\bmat\s+c\b', 'MOTS-c'),
        (r'\bmatsui\b', 'MOTS-c'),
        (r'\bmatsu\b', 'MOTS-c'),
        (r'\bred\s*,?\s+f[u\*][c\*][k\*](?:ing)?\s+t(?:ide|ied)\b', 'Retatrutide'),
        (r'\bred\s+and\b', 'Retatrutide'),
        (r'\bred\s+end\b', 'Retatrutide'),
        (r'\bhard\s+r\b', 'Retatrutide'),
        (r'\bhard-art-art\b', 'Retatrutide'),
        (r'\bhard-art\b', 'Retatrutide'),
        (r'\bslnc\b', 'Selank'),
        (r'\bs-l-n-c\b', 'Selank'),
        (r'\bsalank\b', 'Selank'),
        (r'\bthe\s+big\s+length\b', 'Selank'),
        (r'\bc\s+max\b', 'Semax'),
        (r'\bsermerallin\b', 'Sermorelin'),
        (r'\bsermerall\b', 'Sermorelin'),
        (r'\bsermerellin\b', 'Sermorelin'),
        (r'\bsermorale\b', 'Sermorelin'),
        (r'\bbpc\s*-\s*157\b', 'BPC-157'),
        (r'\bbpc\s+157\b', 'BPC-157'),
        (r'\bbpc157\b', 'BPC-157'),
        (r'\btb\s*-\s*500\b', 'TB-500'),
        (r'\btb\s+500\b', 'TB-500'),
        (r'\btb500\b', 'TB-500'),
        (r'\bghk\s*-\s*cu\b', 'GHK-Cu'),
        (r'\bghk\s+cu\b', 'GHK-Cu'),
        (r'\bghk-c\b', 'GHK-Cu'),
        (r'\bghk\s+c\b', 'GHK-Cu'),
        (r'\btessa\s+ipa\s+blend\b', 'Tesamorelin / Ipamorelin Blend'),
        (r'\btessa\s+ipa\s+psych\b', 'Tesamorelin / Ipamorelin cycle'),
        (r'\btessa\s+ipa\b', 'Tesamorelin / Ipamorelin'),
        (r'\btessa\s+and\s+ipa\b', 'Tesamorelin / Ipamorelin'),
        (r'\btess\s+and\s+ipa\b', 'Tesamorelin / Ipamorelin'),
        (r'\btessa\s+morelana\b', 'Tesamorelin'),
        (r'\bgrowth\s+hormones?\s+to\s+kreeti\s+gog\b', 'growth hormone secretagogue'),
        (r'\bgrowth\s+hormones?\s+to\s+creati\s+gog\b', 'growth hormone secretagogue'),
        (r'\bgrowth\s+hormones?\s+to\s+create\s+a\s+dog\b', 'growth hormone secretagogue'),
        (r'\bmilano\s*-?\s*10\s+(?:too|2)\b', 'Melanotan 2'),
        (r'\bmilano\s*-?\s*10\b', 'Melanotan'),
        (r'\bin\s+clomophine\b', 'enclomiphene'),
        (r'\bin\s+clomiphine\b', 'enclomiphene'),
        (r'\bclomophine\b', 'enclomiphene'),
        (r'\bclomiphine\b', 'enclomiphene'),
        (r'\bfotitti\b', 'Fo-Ti'),
        (r'\bdrop\s+the\s+zal\b', 'drop the cortisol'),
        (r'\binfested\s+with\s+the\s+zal\b', 'infested with the cortisol'),
        (r'\bthe\s+zal\b', 'the cortisol'),
        (r'\bthe\s+big\s+bee\b', 'the big brain'),
        (r'\bcrying\s+and\s+seed\s+on\s+half\s+to\b', 'Trying and See You Don\'t Have To'),
        (r'\bthe\s+getter\s+stack\b', 'the beginner stack'),
    ]
    normalized = text
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized


def classify_video(transcript, title):
    normalized = normalize_transcript(transcript)
    t = normalized.lower()

    if len(normalized) < 200:
        return 'general_advice'

    junk_indicators = ['i\'m gonna be right back', 'they don\'t break on their ass',
                       'from a man named', 'i love it! i got this feeling',
                       'blame, you\'re a little', 'manausages', 'trying and see you don\'t have to']
    if any(j in t for j in junk_indicators):
        return 'general_advice'

    if any(x in t for x in ['peptide', 'bpc', 'tb500', 'ghk', 'ss31', 'mots-c', 'mott c', 'matsu', 'matsui', 'mat-c',
                              'sermerall', 'sermorelin', 'epitale', 'epitalon', 'foxo', 'selank', 'semax', 'kpv', 'dsip', 'd-sip',
                              'melanotan', 'milano', 'thymosin', 'pinealon', 'growth hormone']):
        if any(x in t for x in ['stack', 'protocol', 'phase', 'experiment']):
            return 'peptide_protocol'
        return 'peptide_info'

    if any(x in t for x in ['retitatide', 'retatrutide', 'reta', 'red end', 'red and', 'hard r', 'hard-art', 'glp', 'semaglutide',
                              'tirzepatide']):
        return 'glp1_fat_loss'

    if any(x in t for x in ['testosterone', 'trt', 'hormones', 'test is at', 'estrogen', 'clomiphine', 'enclomiphene']):
        return 'hormones'

    if any(x in t for x in ['mitochondria', 'cellular energy', 'cellular biology', 'ampk', 'miostat']):
        return 'mitochondria'

    if any(x in t for x in ['intermittent fasting', 'fasting', 'calorie', 'protein', 'diet', 'eating', 'macros', 'surplus']):
        return 'nutrition'

    if any(x in t for x in ['cortisol', 'sleep', 'recovery', 'dopamine', 'mental health', 'stress', 'brain']):
        return 'wellness_mindset'

    if any(x in t for x in ['workout', 'gym', 'muscle', 'training', 'cardio', 'exercise', 'physique']):
        return 'fitness'

    if any(x in t for x in ['fda', 'legalized', 'industry', 'western medicine', 'doctors']):
        return 'industry_news'

    return 'general_advice'


def extract_gemini_bullets(transcript, category, api_key=None):
    if not HAS_GENAI:
        return None
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
        cleaned_transcript = normalize_transcript(transcript)

        prompt = f"""You are an expert health and peptide protocol research analyst. Extract highly accurate, specific, and actionable summaries.

Example:
Transcript: "Today's episode is the best things I've learned from my own experiments for anybody who wants to get more out of their peptides. Starting with what's most important to anyone just getting started, inflammation is the killer of all peptides. The whole reason we inject peptides instead of nasal sprays is to get a systematic benefit, meaning our entire body. This is why I recommend almost everybody start with BPC and TB500 to make sure your body can actually receive the signals your peptides are trying to send. You have to take a collagen supplement."
Category: Peptide Protocol
Summary:
- **Compounds mentioned**: BPC-157, TB-500
- **Systemic Inflammation**: He notes that systemic inflammation is the killer of all peptides and blocks their signals.
- **Loading Phase Recommendation**: Recommends starting with BPC-157 and TB-500 to clear inflammation so the body can receive other peptide signals.
- **Collagen co-factor**: Emphasizes that you must take a collagen supplement alongside these peptides.

Analyze this transcript and generate a similar structured summary. No filler or meta-text.

Transcript: "{cleaned_transcript}"
Category: {category}

Return bullets starting with `- `. Include doses if mentioned.
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )

        bullets = []
        for line in response.text.strip().split('\n'):
            line = line.strip()
            if line.startswith('-'):
                bullets.append(line.lstrip('- ').strip())
            elif line:
                bullets.append(line)
        return bullets
    except Exception as e:
        print(f"Error calling Gemini API: {e}", file=sys.stderr)
        return None


def extract_gemini_protocols(transcript, category, api_key=None):
    if not HAS_GENAI:
        return None
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
        cleaned = normalize_transcript(transcript)

        prompt = f"""Analyze this transcript and extract structured protocol data for each compound mentioned.

Transcript: "{cleaned}"
Category: {category}

Return a JSON array where each entry has:
- "compound": exact compound name
- "dose": dosage with unit if mentioned, or null
- "timing": when to take (e.g., "morning", "bedtime", "empty stomach"), or null
- "route": injection method if mentioned (e.g., "subq", "intranasal"), or null
- "frequency": how often (e.g., "daily", "BID", "5 days on/2 off"), or null
- "notes": any important caveats or co-factors, or null
- "confidence": "high", "medium", or "low" based on how clearly stated

Return ONLY valid JSON, no markdown fences.
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return json.loads(text)
    except Exception as e:
        print(f"Error extracting protocols: {e}", file=sys.stderr)
        return None


def extract_fallback_bullets(transcript, category):
    normalized = normalize_transcript(transcript)
    sentences = re.split(r'(?<=[.!?])\s+', normalized.strip())

    clean_sentences = []
    filler_patterns = [
        r"^today's\s+episode", r"^welcome\s+back", r"^if\s+you\s+don't\s+know",
        r"^quick\s+recap", r"^recap\s+if\s+you", r"^in\s+this\s+video",
        r"^i'm\s+constantly\s+researching", r"^i\s+never\s+let\s+comments",
        r"under\s+my\s+skin", r"dumb\s+shit", r"ass\s+doctors",
        r"wasting\s+my\s+money", r"this\s+is\s+what\s+i've\s+been\s+trying",
        r"caught\s+dead\s+going\s+for\s+a", r"sooner\s+be\s+caught",
        r"why\s+are\s+you\s+doing\s+this", r"you\s+guys\s+know",
        r"^i\s+figured\s+it\s+out", r"^i\s+got\s+some\s+good",
        r"it's\s+happening", r"^i'm\s+gonna\s+be\s+right\s+back"
    ]

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        lower_sent = sent.lower()
        if any(re.search(pat, lower_sent) for pat in filler_patterns):
            continue
        clean_sentences.append(sent)

    compounds_found = []
    for c in COMPOUNDS:
        if re.search(r'\b' + re.escape(c.lower()) + r'\b', normalized.lower()):
            compounds_found.append(c)

    bullets = []

    if compounds_found:
        bullets.append(f"**Compounds mentioned**: {', '.join(compounds_found)}")

    action_keywords = ['take', 'taking', 'inject', 'injection', 'subq', 'dose', 'dosing',
                       'mg', 'mcg', 'milligram', 'microgram', 'stack', 'stacking', 'paired',
                       'combine', 'combining', 'morning', 'night', 'bed', 'daily', 'cycle',
                       'week', 'month', 'fasting', 'empty stomach']

    protocol_sentences = []
    seen = set()

    for sent in clean_sentences:
        sent_lower = sent.lower()
        has_compound = any(re.search(r'\b' + re.escape(c.lower()) + r'\b', sent_lower) for c in COMPOUNDS)
        has_action = any(re.search(r'\b' + re.escape(act) + r'\b', sent_lower) for act in action_keywords)

        if has_compound and has_action:
            if sent_lower[:40] not in seen:
                seen.add(sent_lower[:40])
                protocol_sentences.append(sent)

    bullets.extend(protocol_sentences[:4])

    if len(bullets) < 4:
        advice_keywords = ['should', 'need', 'must', 'recommend', 'important', 'crucial', 'key', 'tip', 'advice']
        for sent in clean_sentences:
            sent_lower = sent.lower()
            if any(re.search(pat, sent_lower) for pat in advice_keywords):
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


def extract_fallback_protocols(transcript):
    normalized = normalize_transcript(transcript)
    protocols = []
    seen = set()

    dose_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:mcg|mg|g|ml|iu|units?)',
        r'(\d+(?:\.\d+)?)\s*micrograms?',
        r'(\d+(?:\.\d+)?)\s*milligrams?',
    ]

    timing_patterns = [
        r'(?:morning|evening|night|bedtime|before bed|upon waking|empty stomach|post.?workout|pre.?workout)',
        r'(?:daily|twice daily|BID|TID|once daily|every other day|5 days on)',
    ]

    route_patterns = [
        r'(?:subcutaneous|subq|intramuscular|IM|intranasal|oral|topical)',
    ]

    for c in COMPOUNDS:
        pattern = r'\b' + re.escape(c.lower()) + r'\b'
        for m in re.finditer(pattern, normalized.lower()):
            start = max(0, m.start() - 200)
            end = min(len(normalized), m.end() + 200)
            context = normalized[start:end]
            key = c.lower()
            if key in seen:
                continue
            seen.add(key)

            dose = None
            for pat in dose_patterns:
                dm = re.search(pat, context, re.IGNORECASE)
                if dm:
                    dose = dm.group(0).strip()
                    break

            timing = None
            for pat in timing_patterns:
                tm = re.search(pat, context, re.IGNORECASE)
                if tm:
                    timing = tm.group(0).strip()
                    break

            route = None
            for pat in route_patterns:
                rm = re.search(pat, context, re.IGNORECASE)
                if rm:
                    route = rm.group(0).strip()
                    break

            protocol = {
                "compound": c,
                "dose": dose,
                "timing": timing,
                "route": route,
                "frequency": None,
                "notes": None,
                "confidence": "high" if dose or timing else "low"
            }
            protocols.append(protocol)

    return protocols


def check_interactions(compounds):
    warnings = []
    compound_lower = {c.lower() for c in compounds}
    for pair, msg in INTERACTION_WARNINGS:
        if any(c.lower() in compound_lower for c in pair):
            warnings.append({"compounds": pair, "message": msg})
    return warnings


def generate_topic_summary(transcript):
    sentences = re.split(r'(?<=[.!?])\s+', transcript)
    skip_intros = ['welcome back', 'if you don\'t know me', 'you guys know', 'i got some good',
                   'guys,', 'it\'s happening', 'i figured it out', 'today\'s episode']

    best = None
    for sent in sentences[:5]:
        lower = sent.lower().strip()
        if any(lower.startswith(s) for s in skip_intros):
            continue
        if len(sent.strip()) > 20:
            best = sent.strip()
            break

    if not best:
        best = sentences[0].strip() if sentences else "General discussion"

    if len(best) > 120:
        best = best[:117] + '...'

    return best


def extract_suggestions(transcript, category, api_key=None, return_protocols=False):
    topic = generate_topic_summary(transcript)

    gemini_bullets = extract_gemini_bullets(transcript, category, api_key)
    if gemini_bullets:
        if return_protocols:
            structured = extract_gemini_protocols(transcript, category, api_key)
            return topic, gemini_bullets, structured
        return topic, gemini_bullets

    bullets = extract_fallback_bullets(transcript, category)
    if return_protocols:
        structured = extract_fallback_protocols(transcript)
        return topic, bullets, structured
    return topic, bullets


def extract_video_id(url):
    if not url:
        return None
    match = re.search(r'/video/(\d+)', url)
    if match:
        return match.group(1)
    match = re.search(r'\b\d{18,22}\b', url)
    if match:
        return match.group(0)
    return None


def load_transcript_cache(filepath):
    cache = {}
    if not os.path.exists(filepath):
        return cache
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        blocks = content.split('\n## ')[1:]
        for block in blocks:
            lines = block.strip().split('\n')
            if not lines:
                continue
            title = lines[0].strip()
            url = ""
            transcript_lines = []
            for line in lines[1:]:
                if line.startswith('URL:'):
                    url = line.replace('URL:', '').strip()
                elif line.strip():
                    transcript_lines.append(line.strip())

            transcript = ' '.join(transcript_lines)
            transcript = re.sub(r'\s+', ' ', transcript).strip()

            video_id = extract_video_id(url)
            if video_id:
                cache[video_id] = transcript
    except Exception as e:
        print(f"Error loading transcript cache: {e}")
    return cache


def append_to_transcripts_file(filepath, title, url, transcript):
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n## {title}\nURL: {url}\n\n{transcript}\n\n")
    except Exception as e:
        print(f"Error appending to transcripts: {e}")


def save_srt(segments, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, (start, end, text, conf) in enumerate(segments, 1):
            start_h, start_rem = divmod(start, 3600)
            start_m, start_s = divmod(start_rem, 60)
            start_ms = int((start_s - int(start_s)) * 1000)
            start_s = int(start_s)

            end_h, end_rem = divmod(end, 3600)
            end_m, end_s = divmod(end_rem, 60)
            end_ms = int((end_s - int(end_s)) * 1000)
            end_s = int(end_s)

            start_ts = f"{int(start_h):02d}:{int(start_m):02d}:{start_s:02d},{start_ms:03d}"
            end_ts = f"{int(end_h):02d}:{int(end_m):02d}:{end_s:02d},{end_ms:03d}"

            conf_label = "HIGH" if conf > -0.2 else "MEDIUM" if conf > -0.5 else "LOW"
            f.write(f"{i}\n{start_ts} --> {end_ts}\n[{conf_label}] {text}\n\n")


def save_vtt(segments, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for i, (start, end, text, conf) in enumerate(segments, 1):
            start_h, start_rem = divmod(start, 3600)
            start_m, start_s = divmod(start_rem, 60)
            start_ms = int((start_s - int(start_s)) * 1000)
            start_s = int(start_s)

            end_h, end_rem = divmod(end, 3600)
            end_m, end_s = divmod(end_rem, 60)
            end_ms = int((end_s - int(end_s)) * 1000)
            end_s = int(end_s)

            start_ts = f"{int(start_h):02d}:{int(start_m):02d}:{start_s:02d}.{start_ms:03d}"
            end_ts = f"{int(end_h):02d}:{int(end_m):02d}:{end_s:02d}.{end_ms:03d}"

            conf_label = "HIGH" if conf > -0.2 else "MEDIUM" if conf > -0.5 else "LOW"
            f.write(f"{i}\n{start_ts} --> {end_ts}\n<{conf_label}> {text}\n\n")


def load_job_state(state_path):
    if not os.path.exists(state_path):
        return {"completed": [], "failed": [], "skipped": [], "last_idx": -1}
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"completed": [], "failed": [], "skipped": [], "last_idx": -1}


def save_job_state(state_path, state):
    os.makedirs(os.path.dirname(state_path) or '.', exist_ok=True)
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)


def is_in_state(video_id, state):
    return video_id in state.get("completed", []) or video_id in state.get("failed", [])
