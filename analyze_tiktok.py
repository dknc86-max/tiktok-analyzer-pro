import os
import sys
import argparse
import imageio_ffmpeg
import whisper
import yt_dlp
import warnings
import re
from tqdm import tqdm

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

warnings.filterwarnings("ignore")

# Inject ffmpeg binary into PATH for Whisper dynamically using imageio_ffmpeg
try:
    import imageio_ffmpeg
    ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass

def get_video_entries(profile_url):
    print("Fetching profile metadata...")
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'dump_single_json': True,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(profile_url, download=False)
        return result.get('entries', [result])

def download_audio(video_url, output_path):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'socket_timeout': 15,
        'retries': 3,
        'nocheckcertificate': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

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
        (r'\bred\s+and\b', 'Retatrutide'),
        (r'\bred\s+end\b', 'Retatrutide'),
        (r'\bhard\s+r\b', 'Retatrutide'),
        (r'\bhard-art\b', 'Retatrutide'),
        (r'\bslnc\b', 'Selank'),
        (r'\bs-l-n-c\b', 'Selank'),
        (r'\bc\s+max\b', 'Semax'),
        (r'\bsermerall\b', 'Sermorelin'),
        (r'\bsermerellin\b', 'Sermorelin'),
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
        (r'\btessa\s+ipa\b', 'Tesamorelin / Ipamorelin'),
        (r'\btessa\s+and\s+ipa\b', 'Tesamorelin / Ipamorelin'),
        (r'\btess\s+and\s+ipa\b', 'Tesamorelin / Ipamorelin'),
    ]
    normalized = text
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized


def classify_video(transcript, title):
    """Classify video into a category based on content analysis."""
    t = transcript.lower()
    title_l = title.lower()
    
    if len(transcript) < 200:
        return 'general_advice'
        
    junk_indicators = ['i\'m gonna be right back', 'they don\'t break on their ass',
                       'from a man named', 'i love it! i got this feeling',
                       'blame, you\'re a little', 'manausages']
    if any(j in t for j in junk_indicators):
        return 'general_advice'
        
    if any(x in t for x in ['peptide', 'bpc', 'tb500', 'ghk', 'ss31', 'mots-c', 'mott c', 'matsu', 'matsui', 'mat-c',
                              'sermerall', 'epitale', 'epitalon', 'foxo', 'selank', 'semax', 'kpv', 'dsip', 'd-sip',
                              'melanotan', 'milano', 'thymosin']):
        if any(x in t for x in ['stack', 'protocol', 'phase', 'experiment']):
            return 'peptide_protocol'
        return 'peptide_info'
        
    if any(x in t for x in ['retitatide', 'reta', 'red end', 'red and', 'hard r', 'hard-art', 'glp', 'semaglutide',
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
    """Dual-mode summarizer for the CLI."""
    topic = generate_topic_summary(transcript)
    
    gemini_bullets = extract_gemini_bullets(transcript, category, api_key)
    if gemini_bullets:
        return topic, gemini_bullets
        
    return topic, extract_fallback_bullets(transcript, category)

def summarize_transcripts(transcripts_file, output_file):
    print("Generating summaries...")
    with open(transcripts_file, 'r', encoding='utf-8') as f:
        content = f.read()

    videos = content.split('## ')[1:]
    
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write('# Detailed Video Protocols & Suggestions\n\n')
        out.write('This document highlights the specific recommendations, protocols, and advice discussed in the videos.\n\n')
        
        for video in videos:
            lines = video.strip().split('\n')
            if not lines: continue
            title = lines[0].strip()
            url = ""
            transcript_lines = []
            
            for line in lines[1:]:
                if line.startswith('URL:'):
                    url = line.replace('URL:', '').strip()
                elif line.strip() != '':
                    transcript_lines.append(line.strip())
            
            transcript = " ".join(transcript_lines)
            transcript = re.sub(r'\s+', ' ', transcript)
            
            # Filter out very short videos or just songs
            if len(transcript) < 150 or "song" in transcript.lower():
                continue
            
            category = classify_video(transcript, title)
            topic, suggestions = extract_suggestions(transcript, category)
            
            out.write(f"### [{title}]({url})\n")
            out.write(f"**Topic**: {topic}\n\n")
            out.write("**Key Suggestions / Takeaways**:\n")
            for sug in suggestions:
                out.write(f"- {sug}\n")
            out.write("\n")

def main():
    parser = argparse.ArgumentParser(description="Download, transcribe, and summarize a TikTok profile.")
    parser.add_argument("target", help="The TikTok profile URL (e.g., https://www.tiktok.com/@username) or just the @username")
    args = parser.parse_args()

    target = args.target
    if not target.startswith("http"):
        # Assume it's a username
        if not target.startswith("@"):
            target = "@" + target
        profile_url = f"https://www.tiktok.com/{target}"
        username = target
    else:
        profile_url = target
        username = target.rstrip('/').split('/')[-1]
        if not username.startswith("@"):
            username = "@" + username

    print(f"Target: {username}")
    output_dir = os.path.join("results", username)
    os.makedirs(output_dir, exist_ok=True)
    
    transcripts_file = os.path.join(output_dir, "transcripts.md")
    summaries_file = os.path.join(output_dir, "detailed_summaries.md")

    entries = get_video_entries(profile_url)
    
    if not entries:
        print("No videos found. Check the profile URL.")
        sys.exit(1)
        
    print(f"Found {len(entries)} videos. Loading Whisper model...")
    model = whisper.load_model("tiny.en")
    
    with open(transcripts_file, "w", encoding="utf-8") as f:
        f.write(f"# TikTok Transcripts for {username}\n\n")
        
    for idx, entry in enumerate(tqdm(entries, desc="Transcribing Videos")):
        video_url = entry.get('url') or entry.get('webpage_url')
        if not video_url:
            continue
            
        title = entry.get('title', f"Video {idx+1}")
        tqdm.write(f"\n[{idx+1}/{len(entries)}] Processing: {title}")
        
        audio_path = f"tmp_audio_{idx}.mp3"
        try:
            download_audio(video_url, audio_path)
            result = model.transcribe(audio_path)
            transcript = result["text"].strip()
            
            with open(transcripts_file, "a", encoding="utf-8") as f:
                f.write(f"## {title}\nURL: {video_url}\n\n{transcript}\n\n")
                
        except Exception as e:
            tqdm.write(f"Error on video {idx+1}: {e}")
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
    print("All videos transcribed successfully.")
    
    # Run the summarization
    summarize_transcripts(transcripts_file, summaries_file)
    print(f"\nProcess complete! Results saved in {output_dir}/")

if __name__ == "__main__":
    main()
