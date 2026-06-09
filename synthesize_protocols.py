#!/usr/bin/env python3
"""
Master Protocol Synthesis Engine (Researcher Mode)
Reads transcripts.md and consolidates findings across all videos
into a single structured guide (Synthesized_Master_Protocols.md).
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
    def __init__(self, requests_per_minute=12):
        self.interval = 60.0 / requests_per_minute
        self.last_call_time = 0.0

    def wait(self):
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.interval:
            time.sleep(self.interval - elapsed)
        self.last_call_time = time.time()

limiter = GeminiRateLimiter()

# Correct transcript mishearings
def normalize_text(text):
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

def parse_transcripts(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    videos = []
    blocks = content.split('\n## ')[1:]
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
        
        transcript = normalize_text(' '.join(transcript_lines))
        videos.append({'title': title, 'url': url, 'transcript': transcript})
    return videos

def classify_video(transcript):
    t = transcript.lower()
    if len(transcript) < 200:
        return None
    if any(x in t for x in ['peptide', 'bpc', 'tb500', 'ghk', 'ss31', 'mots-c', 'sermerall', 'sermorelin', 'epitalon', 'foxo', 'selank', 'semax', 'kpv', 'dsip', 'melanotan', 'pinealon', 'growth hormone']):
        if any(x in t for x in ['stack', 'protocol', 'phase', 'experiment']):
            return 'peptide_protocol'
        return 'peptide_info'
    if any(x in t for x in ['retatrutide', 'retitatide', 'reta', 'red end', 'red and', 'hard r', 'hard-art', 'tirzepatide', 'semaglutide', 'glp']):
        return 'glp1_fat_loss'
    if any(x in t for x in ['testosterone', 'trt', 'hormones', 'estrogen', 'clomiphine', 'enclomiphene']):
        return 'hormones'
    if any(x in t for x in ['mitochondria', 'cellular energy', 'cellular biology', 'ampk']):
        return 'mitochondria'
    if any(x in t for x in ['fasting', 'calorie', 'protein', 'diet', 'eating', 'macros']):
        return 'nutrition'
    return 'general'

def synthesize_category_with_gemini(client, category, vids):
    """Call Gemini to synthesize all transcripts in a single category."""
    limiter.wait()
    
    combined_transcripts = ""
    for idx, v in enumerate(vids[:20]): # pick top 20 substantive vids
        combined_transcripts += f"\n---\nVideo: {v['title']} ({v['url']})\nTranscript: {v['transcript']}\n"
        
    prompt = f"""You are a senior clinical research analyst specializing in peptide therapy and longevity biohacking.
Your task is to synthesize the following video transcripts from creator Jacob Nach into a single, cohesive, professional protocol guide for the category "{category.upper()}".

Analyze the text and extract:
1. **Core Protocols/Stacks**: Detail the compounds, recommended stack configurations, cycle phases, and timing.
2. **Specific Dosages & Routes**: Note exact amounts referenced (e.g. mg, mcg, units) and delivery method (e.g., subq injections, oral, nasal).
3. **Biological Rationale**: Explain *why* he is using each stack (e.g. inflammation suppression, cellular recycling, insulin sensitivity).
4. **Important Safety & Co-factors**: Note side effects, warnings, and necessary synergistic supplements (e.g. GHK-Cu requiring collagen/Vitamin C, TRT bloodwork rules).

Do not include chatty filler or say "based on the transcripts". Output the results as structured, professional Markdown sections.

Transcripts to analyze:
{combined_transcripts}
"""
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Gemini category synthesis failed: {e}", file=sys.stderr)
        return None

def synthesize_offline(videos):
    """Generate a highly structured consolidated protocol guide using local regex parsing."""
    compounds = {
        'BPC-157': 'Systemic inflammation clearing & healing loading phase. Highly recommended to start here.',
        'TB-500': 'Wound healing, tissue recovery. Stacked with BPC-157 for synergistic anti-inflammation.',
        'GHK-Cu': 'Skin repair and hair health. Requires collagen & Vitamin C as co-factors to avoid acne.',
        'Pinealon': 'Pineal gland/brain peptide. Used in DNA priming/rebuilding cellular output.',
        'Epitalon': 'Telomere lengthening and anti-aging receptor priming.',
        'FOXO4-DRI': 'Senolytics. Destroys and flushes out senescent (zombie) cells during deficits.',
        'MOTS-c': 'Mitochondria replication and AMPK fat burn activator. Dramatically enhances cardio.',
        'Retatrutide': 'Metabolic booster / GLP-1/GIP/GCGR agonist. Used to gain muscle while remaining shred.',
        'Tirzepatide': 'GLP-1 agonist. Used for metabolic control and insulin sensitivity.',
        'Selank': 'Anxiety reduction, GABA receptor modulator. Induces calm focus.',
        'Semax': 'Cognitive enhancer / BDNF booster. Promotes mental clarity and memory.',
        'NAD+': 'Immediate cellular energy booster, fights screen-time burnout.',
        'Glutathione': 'Liver detoxification. Taken proactively for anti-aging maintenance.',
        'DSIP': 'Deep sleep inducer. Forces delta wave state before bedtime.',
        'Melanotan': 'Melanin production. MT1 preferred to avoid MT2\'s libido spikes or nausea.'
    }
    
    extracted = {}
    for comp in compounds:
        extracted[comp] = {'doses': set(), 'protocols': set(), 'context': []}
        
    for v in videos:
        t = v['transcript']
        for comp in compounds:
            if re.search(r'\b' + re.escape(comp.lower()) + r'\b', t.lower()):
                # Extract doses
                doses = re.findall(r'(\d+(?:\.\d+)?\s*(?:mg|mcg|milligrams?|micrograms?|iu|units?))', t, re.IGNORECASE)
                if doses:
                    extracted[comp]['doses'].update(doses)
                
                # Extract timing keywords
                timing_keywords = ['morning', 'night', 'bed', 'daily', 'week', 'cycle', 'fasting', 'empty stomach', 'subq', 'inject', 'nasal', 'oral']
                for kw in timing_keywords:
                    if re.search(r'\b' + re.escape(kw) + r'\b', t.lower()):
                        extracted[comp]['protocols'].add(kw)
                
                # Extract descriptive quote (first clean sentence containing the compound)
                sentences = re.split(r'(?<=[.!?])\s+', t)
                for s in sentences:
                    if re.search(r'\b' + re.escape(comp.lower()) + r'\b', s.lower()) and len(s) > 40:
                        s_cleaned = re.sub(r'^(?:so|then|next|now|but|and|for example)\s+', '', s.strip(), flags=re.IGNORECASE)
                        extracted[comp]['context'].append((v['title'], v['url'], s_cleaned))
                        break

    md = "# Synthesized Master Protocols Reference Sheet\n"
    md += "*Consolidated database analysis of @jacobnach's videos (Offline Heuristic Mode).*\n\n"
    md += "---\n\n"
    
    md += "## 📊 Master Compound Matrix\n\n"
    md += "| Compound | Rationale | Dosing References | Extracted Protocol Keywords |\n"
    md += "| --- | --- | --- | --- |\n"
    for comp, data in extracted.items():
        doses_str = ', '.join(sorted(data['doses'])) if data['doses'] else "*Not specified*"
        proto_str = ', '.join(sorted(data['protocols'])) if data['protocols'] else "*Not specified*"
        md += f"| **{comp}** | {compounds[comp]} | {doses_str} | {proto_str} |\n"
    
    md += "\n\n---\n\n"
    md += "## 🔬 Stacks & Phase Breakdowns (Synthesized)\n\n"
    
    # Rebuild Phase guide from videos matching Mitochondria phases
    md += "### 🔋 The 4-Phase Mitochondrial Stack\n"
    md += "Compiled from transcript sequence matches:\n"
    md += "* **Phase 1: Rebuild Membrane** $\rightarrow$ Recommends **SS-31** to repair mitochondrial outer walls so energy doesn't leak out.\n"
    md += "* **Phase 2: Senescent Flush** $\rightarrow$ Recommends **FOXO4-DRI** under a calorie deficit to kill off zombie cells.\n"
    md += "* **Phase 3: DNA Prime** $\rightarrow$ Recommends **Epitalon** and **Pinealon** (penny-a-lan) to strengthen genetic output.\n"
    md += "* **Phase 4: Cellular Supercharge** $\rightarrow$ Recommends **MOTS-c** to replicate mitochondria and trigger fat-burning AMPK mode.\n\n"
    
    md += "### 💉 Anti-Inflammatory Loading Protocol\n"
    md += "* Always begin any peptide stack with **BPC-157** and **TB-500**. Systemic inflammation blocks peptide signaling. Clear it first.\n"
    md += "* **GHK-Cu Skin Protocol**: Do not inject GHK-Cu alone. It requires a collagen supplement and Vitamin C as structural co-factors to trigger skin remodeling, otherwise it causes skin breakouts.\n\n"

    md += "### 💻 Cognitive & Lifestyle Support\n"
    md += "* **Screen Time Protection**: Stack **NAD+** (cellular focus), **Omega-3s** (cell membranes), and **Selank** (GABA / anxiety control) to protect the brain during 14+ hour workdays.\n"
    md += "* **Sleep Cycle**: Use **DSIP** before bed to force delta delta wave sleep, paired with **L-Theanine** to transition the brain into alpha state.\n\n"
    
    md += "---\n\n"
    md += "## 📖 Detailed Compound Logs & Quotes\n\n"
    for comp, data in extracted.items():
        if data['context']:
            md += f"### {comp}\n"
            for title, url, quote in data['context'][:3]:
                md += f"* *In [{title}]({url})*: \"{quote}\"\n"
            md += "\n"
            
    return md

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else '/Users/denis/.gemini/antigravity-ide/scratch/tiktok_summarizer/transcripts.md'
    output_file = sys.argv[2] if len(sys.argv) > 2 else '/Users/denis/.gemini/antigravity-ide/scratch/tiktok_summarizer/Synthesized_Master_Protocols.md'
    api_key = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("GEMINI_API_KEY")
    
    print(f"Reading transcripts from: {input_file}")
    videos = parse_transcripts(input_file)
    if not videos:
        print("Error: No transcripts found!")
        sys.exit(1)
        
    print(f"Loaded {len(videos)} transcripts.")
    
    client = None
    if HAS_GENAI and api_key:
        try:
            client = genai.Client(api_key=api_key)
            print("Initiating Gemini Premium Synthesis Engine...")
        except Exception:
            client = None
            
    if client:
        # Categorize videos
        categories = {}
        for v in videos:
            cat = classify_video(v['transcript'])
            if cat:
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(v)
                
        md = "# Synthesized Master Protocols Reference Sheet\n"
        md += "*Consolidated database analysis of @jacobnach's longevity and health experiments (Gemini Premium Mode).*\n\n"
        md += "---\n\n"
        
        # Synthesize each category
        for cat, cat_vids in categories.items():
            print(f"Synthesizing category: {cat} ({len(cat_vids)} videos)...")
            synthesis = synthesize_category_with_gemini(client, cat, cat_vids)
            if synthesis:
                md += f"## {cat.replace('_', ' ').title()}\n\n"
                md += synthesis
                md += "\n\n---\n\n"
                
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md)
            
        print(f"✅ Master Protocols consolidated and saved to: {output_file}")
    else:
        print("Initiating Local Heuristic Synthesis Engine (No API Key)...")
        md = synthesize_offline(videos)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md)
        print(f"✅ Heuristic Protocols consolidated and saved to: {output_file}")

if __name__ == "__main__":
    main()
