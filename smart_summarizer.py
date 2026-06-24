#!/usr/bin/env python3
"""
Smart TikTok Video Summarizer
Reads raw transcripts and produces high-quality, human-written-style bullet points
by analyzing content structure rather than just keyword matching.
"""

import os
import re
import sys
import time
from logger import get_logger

import config

logger = get_logger("smart_summarizer")

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class GeminiRateLimiter:
    """Rate limiter to respect Gemini API Free Tier limits."""

    def __init__(self, requests_per_minute: int = None):
        requests_per_minute = requests_per_minute or config.GEMINI_MAX_REQUESTS_PER_MINUTE
        self.interval = 60.0 / requests_per_minute
        self.last_call_time = 0.0

    def wait(self) -> None:
        """Wait to maintain rate limit."""
        now = time.time()
        elapsed = now - self.last_call_time
        if elapsed < self.interval:
            sleep_time = self.interval - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self.last_call_time = time.time()


# Global rate limiter instance
limiter = GeminiRateLimiter()


def parse_transcripts(filepath: str) -> list:
    """
    Parse transcripts from markdown file.
    
    Args:
        filepath: Path to transcripts.md file
        
    Returns:
        List of transcript dictionaries
    """
    logger.info(f"Parsing transcripts from {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    videos = []
    blocks = content.split("\n## ")[1:]  # skip header

    for block in blocks:
        lines = block.strip().split("\n")
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

        videos.append({"title": title, "url": url, "transcript": transcript})

    logger.info(f"Parsed {len(videos)} transcripts")
    return videos


def normalize_transcript(text: str) -> str:
    """Normalize transcript text (imported from core for consistency)."""
    from core import normalize_transcript as core_normalize
    return core_normalize(text)


def classify_video(transcript: str, title: str = "") -> str:
    """Classify video content (imported from core for consistency)."""
    from core import classify_video as core_classify
    return core_classify(transcript, title)


def extract_gemini_bullets(transcript: str, category: str, api_key: str = None) -> list:
    """
    Extract bullet points using Gemini API with rate limiting.
    
    Args:
        transcript: Video transcript
        category: Content category
        api_key: Gemini API key (uses config if None)
        
    Returns:
        List of bullet strings or None
    """
    if not HAS_GENAI:
        return None

    api_key = api_key or config.GEMINI_API_KEY
    if not api_key:
        return None

    try:
        limiter.wait()

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
    """Extract bullets using heuristic pattern matching."""
    from core import extract_fallback_bullets as core_fallback
    return core_fallback(transcript, category)


def extract_smart_bullets(transcript: str, category: str, api_key: str = None) -> list:
    """
    Dual-mode extraction: Try Gemini API first, fall back to heuristic.

    Args:
        transcript: Video transcript
        category: Content category
        api_key: Optional API key override

    Returns:
        List of bullet strings
    """
    gemini_bullets = extract_gemini_bullets(transcript, category, api_key)
    if gemini_bullets:
        logger.debug("Used Gemini API for summary")
        return gemini_bullets

    logger.debug("Used fallback heuristic for summary")
    return extract_fallback_bullets(transcript, category)


def generate_topic_summary(transcript: str) -> str:
    """Generate a short topic summary from transcript."""
    from core import generate_topic_summary as core_summary
    return core_summary(transcript)


CATEGORY_LABELS = {
    "peptide_protocol": "💉 Peptide Protocol",
    "peptide_info": "💊 Peptide Info",
    "glp1_fat_loss": "🔥 Fat Loss / GLP-1",
    "hormones": "🧬 Hormones & TRT",
    "mitochondria": "⚡ Mitochondria",
    "nutrition": "🥩 Nutrition & Diet",
    "wellness_mindset": "🧠 Wellness & Mindset",
    "fitness": "💪 Fitness",
    "industry_news": "📰 Industry News",
    "general_advice": "💡 General Advice",
}


def main() -> None:
    """Main entry point."""
    input_file = sys.argv[1] if len(sys.argv) > 1 else str(config.TRANSCRIPTS_FILE)
    output_file = (
        sys.argv[2]
        if len(sys.argv) > 2
        else str(config.RESULTS_DIR / "detailed_video_summaries.md")
    )

    if not os.path.exists(input_file):
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)

    logger.info(f"Reading transcripts from: {input_file}")
    videos = parse_transcripts(input_file)

    # Classify and process — deduplicate by URL
    categorized = {}
    skipped = 0
    seen_urls = set()

    for video in videos:
        # Deduplicate by URL
        if video["url"] in seen_urls:
            skipped += 1
            continue
        seen_urls.add(video["url"])

        category = classify_video(video["transcript"], video["title"])
        if category == "general_advice" and len(video["transcript"]) < 300:
            skipped += 1
            continue

        if category not in categorized:
            categorized[category] = []

        topic = generate_topic_summary(video["transcript"])
        bullets = extract_smart_bullets(video["transcript"], category)

        categorized[category].append(
            {
                "title": video["title"],
                "url": video["url"],
                "topic": topic,
                "bullets": bullets,
            }
        )

    logger.info(f"Skipped {skipped} non-substantive videos")
    logger.info(f"Categorized into {len(categorized)} categories")

    # Write output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Complete Video Breakdown\n\n")
        f.write(
            "Every substantive video organized by topic, with extracted protocols, compounds, dosing, and actionable advice.\n\n"
        )
        f.write("---\n\n")

        # Order categories logically
        category_order = [
            "peptide_protocol",
            "peptide_info",
            "mitochondria",
            "glp1_fat_loss",
            "hormones",
            "nutrition",
            "fitness",
            "wellness_mindset",
            "industry_news",
            "general_advice",
        ]

        for cat in category_order:
            if cat not in categorized:
                continue

            vids = categorized[cat]
            label = CATEGORY_LABELS.get(cat, cat)

            f.write(f"## {label} ({len(vids)} videos)\n\n")

            for vid in vids:
                f.write(f"### [{vid['title']}]({vid['url']})\n")
                f.write(f"> {vid['topic']}\n\n")

                for bullet in vid["bullets"]:
                    f.write(f"- {bullet}\n")

                f.write("\n")

            f.write("---\n\n")

    # Print summary stats
    total_processed = sum(len(v) for v in categorized.values())
    logger.info(f"✅ Done! Wrote {total_processed} video summaries to: {output_file}")
    logger.info("Breakdown by category:")
    for cat in category_order:
        if cat in categorized:
            label = CATEGORY_LABELS.get(cat, cat)
            logger.info(f"  {label}: {len(categorized[cat])} videos")


if __name__ == "__main__":
    main()
