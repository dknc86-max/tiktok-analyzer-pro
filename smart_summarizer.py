#!/usr/bin/env python3
"""
Smart TikTok Video Summarizer
Reads raw transcripts and produces high-quality, human-written-style bullet points
by actually understanding the content rather than just keyword matching.
"""

import os
import re
import sys
import time

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class GeminiRateLimiter:
    """Rate limiter to stay below Gemini API Free Tier 15 RPM ceiling."""
    def __init__(self, requests_per_minute=12):
        self.interval = 60.0 / requests_per_minute
        self.last_call_time = 0.0

    def wait(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.interval:
            sleep_time = self.interval - elapsed
            time.sleep(sleep_time)
        self.last_call_time = time.time()

# Global rate limiter instance
limiter = GeminiRateLimiter()

def parse_transcripts(filepath):
    """Parse the transcripts.md file into a list of video dicts."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    videos = []
    blocks = content.split('\n## ')[1:]  # skip header
    
    for block in blocks:
        lines = block.strip().split('\n')
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
        
        videos.append({
            'title': title,
            'url': url,
            'transcript': transcript
        })
    
    return videos


def classify_video(transcript, title):
    """Classify video into a category based on content analysis."""
    t = transcript.lower()
    title_l = title.lower()
    
    # Skip junk / music / very short
    if len(transcript) < 200:
        return 'skip'
    
    # Check if it's mostly music/lyrics/nonsense
    junk_indicators = ['i\'m gonna be right back', 'they don\'t break on their ass',
                       'from a man named', 'i love it! i got this feeling',
                       'blame, you\'re a little', 'manausages']
    if any(j in t for j in junk_indicators):
        return 'skip'
    
    # Categorize
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
    
    if len(transcript) > 400:
        return 'general_advice'
    
    return 'skip'


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


def extract_gemini_bullets(transcript, category, api_key=None):
    """Call Gemini 2.5 Flash to extract high-quality structured protocols."""
    if not HAS_GENAI:
        return None
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        # Respect rate limiting
        limiter.wait()
        
        client = genai.Client(api_key=api_key)
        # Normalize transcript first to help the LLM
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
    """Extract structured, researcher-style semantic protocol bullets from normalized text."""
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
    
    compounds_found = {}
    
    # 1. Identify compounds & context sentences
    for c in compounds:
        c_lower = c.lower()
        context_sents = []
        for sent in clean_sentences:
            if re.search(r'\b' + re.escape(c_lower) + r'\b', sent.lower()):
                context_sents.append(sent)
        if context_sents:
            compounds_found[c] = context_sents

    bullets = []
    
    if compounds_found:
        bullets.append(f"**Compounds mentioned**: {', '.join(compounds_found.keys())}")
        
        # 2. Structured details per compound
        for comp, sents in compounds_found.items():
            # Look for doses
            doses = []
            for s in sents:
                dose_matches = re.findall(r'(\d+(?:\.\d+)?\s*(?:mg|mcg|milligrams?|micrograms?|grams?|iu|units?))', s, re.IGNORECASE)
                if dose_matches:
                    doses.extend(dose_matches)
            doses = list(dict.fromkeys(doses))
            dose_str = f"Dosing: {', '.join(doses)}" if doses else ""
            
            # Look for timing/action
            timing = []
            timing_keywords = ['morning', 'night', 'bed', 'daily', 'week', 'cycle', 'fasting', 'empty stomach', 'subq', 'inject']
            for s in sents:
                s_lower = s.lower()
                for kw in timing_keywords:
                    if re.search(r'\b' + re.escape(kw) + r'\b', s_lower):
                        timing.append(kw)
            timing = list(dict.fromkeys(timing))
            timing_str = f"Protocol: {', '.join(timing)}" if timing else ""
            
            desc_sentence = sents[0]
            desc_sentence = re.sub(r'^(?:so|then|next|now|but|and|for example)\s+', '', desc_sentence, flags=re.IGNORECASE)
            
            details = []
            if dose_str: details.append(dose_str)
            if timing_str: details.append(timing_str)
            
            detail_tag = f" ({'; '.join(details)})" if details else ""
            bullets.append(f"**{comp}**{detail_tag}: {desc_sentence}")
    
    # 3. Add general advice if bullets are sparse
    if len(bullets) < 3:
        advice_keywords = ['should', 'need', 'must', 'recommend', 'important', 'crucial', 'key', 'tip', 'advice']
        seen = set()
        for sent in clean_sentences:
            sent_lower = sent.lower()
            if any(re.search(r'\b' + re.escape(adv) + r'\b', sent_lower) for adv in advice_keywords):
                if sent_lower[:40] not in seen:
                    seen.add(sent_lower[:40])
                    bullets.append(sent)
                    if len(bullets) >= 5:
                        break
                        
    if len(bullets) < 2:
        for sent in clean_sentences[:3]:
            bullets.append(sent)
            
    return bullets


def extract_smart_bullets(transcript, category):
    """
    Dual-mode summary: Try Gemini API first (with rate limit), fail over to the improved
    structured semantic fallback parser.
    """
    gemini_bullets = extract_gemini_bullets(transcript, category)
    if gemini_bullets:
        return gemini_bullets
        
    return extract_fallback_bullets(transcript, category)


def generate_topic_summary(transcript):
    """Generate a short, meaningful topic line from the transcript."""
    sentences = re.split(r'(?<=[.!?])\s+', transcript)
    
    # Skip generic intros
    skip_intros = ['welcome back', 'if you don\'t know me', 'you guys know', 'i got some good',
                   'guys,', 'it\'s happening', 'i figured it out']
    
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
    
    # Truncate if too long
    if len(best) > 120:
        best = best[:117] + '...'
    
    return best


CATEGORY_LABELS = {
    'peptide_protocol': '💉 Peptide Protocol',
    'peptide_info': '💊 Peptide Info',
    'glp1_fat_loss': '🔥 Fat Loss / GLP-1',
    'hormones': '🧬 Hormones & TRT',
    'mitochondria': '⚡ Mitochondria',
    'nutrition': '🥩 Nutrition & Diet',
    'wellness_mindset': '🧠 Wellness & Mindset',
    'fitness': '💪 Fitness',
    'industry_news': '📰 Industry News',
    'general_advice': '💡 General Advice',
}


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else '/Users/denis/.gemini/antigravity-ide/scratch/tiktok_summarizer/transcripts.md'
    output_file = sys.argv[2] if len(sys.argv) > 2 else '/Users/denis/.gemini/antigravity-ide/brain/1b237685-ae09-418a-bbe9-4aee47dd0d72/detailed_video_summaries.md'
    
    print(f"Reading transcripts from: {input_file}")
    videos = parse_transcripts(input_file)
    print(f"Parsed {len(videos)} videos")
    
    # Classify and process — deduplicate by URL
    categorized = {}
    skipped = 0
    seen_urls = set()
    
    for video in videos:
        # Deduplicate by URL
        if video['url'] in seen_urls:
            skipped += 1
            continue
        seen_urls.add(video['url'])
        
        category = classify_video(video['transcript'], video['title'])
        if category == 'skip':
            skipped += 1
            continue
        
        if category not in categorized:
            categorized[category] = []
        
        topic = generate_topic_summary(video['transcript'])
        bullets = extract_smart_bullets(video['transcript'], category)
        
        categorized[category].append({
            'title': video['title'],
            'url': video['url'],
            'topic': topic,
            'bullets': bullets,
        })
    
    print(f"Skipped {skipped} non-substantive videos")
    print(f"Categorized into {len(categorized)} categories")
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Jacob Nach (@jacobnach) — Complete Video Breakdown\n\n")
        f.write("Every substantive video organized by topic, with extracted protocols, compounds, dosing, and actionable advice.\n\n")
        f.write("---\n\n")
        
        # Order categories logically
        category_order = ['peptide_protocol', 'peptide_info', 'mitochondria', 'glp1_fat_loss',
                          'hormones', 'nutrition', 'fitness', 'wellness_mindset', 'industry_news', 'general_advice']
        
        for cat in category_order:
            if cat not in categorized:
                continue
            
            vids = categorized[cat]
            label = CATEGORY_LABELS.get(cat, cat)
            
            f.write(f"## {label} ({len(vids)} videos)\n\n")
            
            for vid in vids:
                f.write(f"### [{vid['title']}]({vid['url']})\n")
                f.write(f"> {vid['topic']}\n\n")
                
                for bullet in vid['bullets']:
                    f.write(f"- {bullet}\n")
                
                f.write("\n")
            
            f.write("---\n\n")
    
    # Print summary stats
    total_processed = sum(len(v) for v in categorized.values())
    print(f"\n✅ Done! Wrote {total_processed} video summaries to: {output_file}")
    print(f"\nBreakdown by category:")
    for cat in category_order:
        if cat in categorized:
            label = CATEGORY_LABELS.get(cat, cat)
            print(f"  {label}: {len(categorized[cat])} videos")


if __name__ == "__main__":
    main()
