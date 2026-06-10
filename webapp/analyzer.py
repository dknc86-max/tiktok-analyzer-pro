import os
import re
import sys
<<<<<<< HEAD
import json
=======
>>>>>>> origin/main
import glob
import signal
import threading
import sqlite3
import yt_dlp
import warnings
from queue import Queue

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core import (
    download_audio, get_video_entries, transcribe_audio, normalize_transcript,
    classify_video, extract_gemini_bullets, extract_fallback_bullets,
    generate_topic_summary, extract_suggestions, extract_video_id,
    load_transcript_cache, append_to_transcripts_file, HAS_GENAI,
<<<<<<< HEAD
    USE_FASTER, WhisperModel, extract_dosages, compact_transcripts_cache
=======
    USE_FASTER, WhisperModel, load_whisper_model
>>>>>>> origin/main
)

warnings.filterwarnings("ignore")

DEFAULT_TRANSCRIPTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'transcripts.md'
)

<<<<<<< HEAD
JOB_STATE_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'job_state.db'
)


def get_db():
    conn = sqlite3.connect(JOB_STATE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'starting',
            progress INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            current_video TEXT DEFAULT '',
            message TEXT DEFAULT '',
            results_json TEXT DEFAULT '[]',
            dosages_json TEXT DEFAULT '[]',
            target TEXT DEFAULT '',
            max_videos INTEGER DEFAULT 50,
            api_key TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


init_db()


def db_upsert_job(job_id, **kwargs):
    conn = get_db()
    existing = conn.execute("SELECT job_id FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    if existing:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [job_id]
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE job_id = ?", values)
    else:
        cols = ", ".join(["job_id"] + list(kwargs.keys()))
        placeholders = ", ".join(["?"] * (1 + len(kwargs)))
        values = [job_id] + list(kwargs.values())
        conn.execute(f"INSERT INTO jobs ({cols}) VALUES ({placeholders})", values)
    conn.commit()
    conn.close()


def db_get_job(job_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        try:
            d["results"] = json.loads(d.pop("results_json", "[]"))
        except Exception:
            d["results"] = []
        try:
            d["dosages"] = json.loads(d.pop("dosages_json", "[]"))
        except Exception:
            d["dosages"] = []
        d.setdefault("target", "")
        d.setdefault("max_videos", 50)
        d.setdefault("api_key", "")
        return d
    return None


def db_list_jobs():
    conn = get_db()
    rows = conn.execute("SELECT job_id, status, progress, total, message, created_at FROM jobs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


import json


=======

>>>>>>> origin/main
def cleanup_temp_files():
    pattern = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp_audio_*.mp3')
    for f in glob.glob(pattern):
        try:
            os.remove(f)
        except OSError:
            pass

<<<<<<< HEAD
=======

>>>>>>> origin/main
def signal_handler(signum, frame):
    cleanup_temp_files()
    sys.exit(0)

<<<<<<< HEAD
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def transcribe_audio(model, audio_path):
    """Transcribe using whichever whisper engine is available."""
    if USE_FASTER:
        segments, _ = model.transcribe(audio_path, language="en", beam_size=1)
        return " ".join(seg.text for seg in segments).strip()
    else:
        result = model.transcribe(audio_path)
        return result["text"].strip()


def normalize_transcript(text):
    """Clean up common Whisper ASR phonetics and typos for peptides and compounds."""
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
    """Classify video into a category based on content analysis."""
    # Run classification on the normalized transcript for maximum accuracy!
    normalized = normalize_transcript(transcript)
    t = normalized.lower()
    title_l = title.lower()
    
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
    """Call Gemini 2.5 Flash to extract high-quality structured protocols."""
    if not HAS_GENAI:
        return None
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        client = genai.Client(api_key=api_key)
        cleaned_transcript = normalize_transcript(transcript)
        
        prompt = f"""You are an expert health and peptide protocol research analyst. Your job is to extract highly accurate, specific, and actionable summaries from transcripts of short video clips.

Here is an example of a high-quality manual summary:
Transcript: "Today's episode is the best things I've learned from my own experiments on myself and my own research for anybody who wants to get more out of their peptides or is thinking about starting. Starting with what's probably the most important to anyone who's just getting started, inflammation is the killer of all peptides. The whole reason we inject peptides instead of nasal sprays or aurals is to get a systematic benefit, meaning our entire body. This is why I recommend almost everybody start with BPC and TB500 to make sure your body can actually receive the signals your peptides are trying to send. You have to take a collagen supplement."
Category: Peptide Protocol
Summary:
- **Compounds mentioned**: BPC-157, TB-500
- **Systemic Inflammation**: He notes that systemic inflammation is the killer of all peptides and blocks their signals.
- **Loading Phase Recommendation**: Recommends starting with BPC-157 and TB-500 to clear inflammation so the body can receive other peptide signals.
- **Collagen co-factor**: Emphasizes that you must take a collagen supplement alongside these peptides.

Now, analyze the following video transcript and category, and generate a similar, high-quality, structured summary. Do not include conversational filler, meta-text, or intros (like "This video discusses..."). Focus purely on the compounds, protocols, dosing, and actionable advice.

Transcript: "{cleaned_transcript}"
Category: {category}

Return the summary as a list of bullet points starting directly with `- `. Make each bullet point concise and clear. If a compound has a specific dose mentioned, make sure to include it.
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


def extract_fallback_bullets(transcript, category):
    """Extract clean, substantive bullets using pattern matching on normalized text."""
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
        r"i\s+figured\s+it\s+out", r"i\s+got\s+some\s+good",
        r"it's\s+happening", r"i'm\s+gonna\s+be\s+right\s+back"
    ]
    
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        lower_sent = sent.lower()
        if any(re.search(pat, lower_sent) for pat in filler_patterns):
            continue
        clean_sentences.append(sent)
        
    compounds = ['BPC-157', 'TB-500', 'GHK-Cu', 'KPV', 'Pinealon', 'Epitalon', 
                 'FOXO4-DRI', 'Selank', 'Semax', 'MOTS-c', 'Retatrutide', 'Tirzepatide', 
                 'Semaglutide', 'Tesamorelin', 'Ipamorelin', 'TRT', 'Testosterone', 
                 'Glutathione', 'NAD+', 'Sermorelin', 'Dihexa', 'DSIP', 'Melanotan']
                 
    compounds_found = []
    for c in compounds:
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
        has_compound = any(re.search(r'\b' + re.escape(c.lower()) + r'\b', sent_lower) for c in compounds)
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


def generate_topic_summary(transcript):
    """Generate a short, meaningful topic line from the transcript."""
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


def extract_suggestions(transcript, category, api_key=None):
    """Dual-mode summarizer for the webapp."""
    topic = generate_topic_summary(transcript)
    
    gemini_bullets = extract_gemini_bullets(transcript, category, api_key)
    if gemini_bullets:
        return topic, gemini_bullets
        
    return topic, extract_fallback_bullets(transcript, category)


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


def analyze_profile_background(job_id, target, api_key=None, max_videos=50, resume_from=0):
    db_upsert_job(job_id,
        status="starting",
        progress=resume_from,
        total=0,
        current_video="",
        message="Fetching profile metadata...",
        results_json="[]",
        dosages_json="[]",
        target=target,
        max_videos=max_videos,
        api_key=api_key or ""
    )

    transcripts_path = DEFAULT_TRANSCRIPTS_PATH
=======

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

jobs = {}


def analyze_profile_background(job_id, target, api_key=None, max_videos=50):
    jobs[job_id] = {
        "status": "starting",
        "progress": 0,
        "total": 0,
        "current_video": "",
        "message": "Fetching profile metadata...",
        "results": []
    }
>>>>>>> origin/main

    transcripts_path = DEFAULT_TRANSCRIPTS_PATH

    try:
        if not target.startswith("http"):
            if not target.startswith("@"):
                target = "@" + target
            profile_url = f"https://www.tiktok.com/{target}"
        else:
            profile_url = target

        ydl_opts = {
            'extract_flat': 'in_playlist',
            'dump_single_json': True,
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(profile_url, download=False)
            entries = result.get('entries', [result])

        if not entries:
            db_upsert_job(job_id, status="error", message="No videos found. Check the profile URL.")
            return

        if max_videos and max_videos > 0:
            entries = entries[:max_videos]

        total_videos = len(entries)
        db_upsert_job(job_id, status="transcribing", total=total_videos,
                       message=f"Found {total_videos} videos. Loading AI model...")

        cache = load_transcript_cache(transcripts_path)

<<<<<<< HEAD
        if os.path.getsize(transcripts_path) > 10 * 1024 * 1024:
            compact_transcripts_cache(transcripts_path)

        if USE_FASTER:
            model = WhisperModel("tiny.en", compute_type="int8")
        else:
            import torch
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            import whisper
            model = whisper.load_model("tiny.en", device=device)
=======
        model, device = load_whisper_model("small.en")
>>>>>>> origin/main

        extracted_data = []
        extracted_dosages = []

        download_queue = Queue(maxsize=2)

        def prefetch_worker():
            for idx, entry in enumerate(entries):
                if idx < resume_from:
                    download_queue.put(None)
                    continue
                video_url = entry.get('url') or entry.get('webpage_url')
                if not video_url:
                    download_queue.put(None)
                    continue
                title = entry.get('title', f"Video {idx+1}")

                video_id = extract_video_id(video_url)
                if video_id and video_id in cache:
                    download_queue.put((idx, title, video_url, None, cache[video_id]))
                    continue

                audio_path = f"tmp_audio_{job_id}_{idx}.mp3"
                try:
                    dl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': audio_path,
                        'quiet': True,
                        'socket_timeout': 15,
                        'retries': 3,
                        'nocheckcertificate': True,
                    }
                    with yt_dlp.YoutubeDL(dl_opts) as ydl:
                        ydl.download([video_url])
                    download_queue.put((idx, title, video_url, audio_path, None))
                except Exception:
                    download_queue.put(None)
            download_queue.put("DONE")

        prefetch_thread = threading.Thread(target=prefetch_worker, daemon=True)
        prefetch_thread.start()

        skipped = 0
        while True:
            item = download_queue.get()

            if item == "DONE":
                break

            if item is None:
                skipped += 1
                continue

            idx, title, video_url, audio_path, cached_transcript = item
            db_upsert_job(job_id, progress=idx + 1, current_video=title)

            try:
                if cached_transcript is not None:
                    db_upsert_job(job_id, message=f"⚡ Loading cached transcript for video {idx+1} of {total_videos}...")
                    transcript = cached_transcript
                else:
                    db_upsert_job(job_id, message=f"⚡ Transcribing video {idx+1} of {total_videos}...")
                    transcript = transcribe_audio(model, audio_path)
                    append_to_transcripts_file(transcripts_path, title, video_url, transcript)

                transcript = re.sub(r'\s+', ' ', transcript)

                if len(transcript) > 150 and "song" not in transcript.lower():
                    category = classify_video(transcript, title)
                    topic, suggestions = extract_suggestions(transcript, category, api_key)
                    dosages = extract_dosages(transcript, title, video_url)

                    extracted_data.append({
                        "title": title,
                        "url": video_url,
                        "topic": topic,
                        "category": category,
                        "suggestions": suggestions,
                        "transcript": transcript
                    })
                    extracted_dosages.extend(dosages)

            except Exception as e:
                print(f"Error on video {idx+1}: {e}")
            finally:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)

        prefetch_thread.join()

        db_upsert_job(job_id,
            status="completed",
            message="Analysis complete!",
            results_json=json.dumps(extracted_data),
            dosages_json=json.dumps(extracted_dosages)
        )

    except Exception as e:
        db_upsert_job(job_id, status="error", message=str(e))


def start_analysis(target, api_key=None, max_videos=50):
    job_id = re.sub(r'[^a-zA-Z0-9]', '_', target.lower())

    existing = db_get_job(job_id)
    if existing and existing.get("status") in ("completed", "error", "transcribing"):
        resume_from = existing.get("progress", 0) if existing.get("status") == "error" else 0
        thread = threading.Thread(target=analyze_profile_background, args=(job_id, target, api_key, max_videos, resume_from))
        thread.start()
    elif not existing:
        thread = threading.Thread(target=analyze_profile_background, args=(job_id, target, api_key, max_videos, 0))
        thread.start()

    return job_id


def get_job_status(job_id):
    job = db_get_job(job_id)
    if not job:
        return {"status": "not_found", "message": "Job not found"}
    job.pop("job_id", None)
    return job


def list_jobs():
    return db_list_jobs()


def resume_job(job_id):
    job = db_get_job(job_id)
    if not job:
        return None
    if job.get("status") not in ("error", "transcribing"):
        return None
    resume_from = job.get("progress", 0)
    target = job.get("target", job_id)
    api_key = job.get("api_key")
    max_videos = job.get("max_videos", 50)
    db_upsert_job(job_id, status="starting", message="Resuming analysis...")
    thread = threading.Thread(target=analyze_profile_background, args=(job_id, target, api_key, max_videos, resume_from))
    thread.start()
    return job_id
