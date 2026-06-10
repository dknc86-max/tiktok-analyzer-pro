import os
import sys
import argparse
import signal
import glob
import torch

from core import (
    get_video_entries, download_audio, normalize_transcript, classify_video,
    extract_suggestions, extract_video_id, load_transcript_cache,
    append_to_transcripts_file, USE_FASTER, WhisperModel,
    load_whisper_model
)

DEFAULT_TRANSCRIPTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "transcripts.md"
)


def cleanup_temp_files():
    pattern = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_audio_*.mp3")
    for f in glob.glob(pattern):
        try:
            os.remove(f)
        except OSError:
            pass


def signal_handler(signum, frame):
    cleanup_temp_files()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def summarize_transcripts(transcripts_file, output_file):
    import re

    print("Generating summaries...")
    with open(transcripts_file, 'r', encoding='utf-8') as f:
        content = f.read()

    videos = content.split('## ')[1:]

    with open(output_file, 'w', encoding='utf-8') as out:
        out.write('# Detailed Video Protocols & Suggestions\n\n')
        out.write('This document highlights the specific recommendations, protocols, and advice discussed in the videos.\n\n')

        for video in videos:
            lines = video.strip().split('\n')
            if not lines:
                continue
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
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of videos to download and transcribe (default: 50, use 0 for all)")
    parser.add_argument("--transcripts-path", default=None, help="Path to shared transcripts cache file (default: ./transcripts.md)")
    args = parser.parse_args()

    target = args.target
    limit = args.limit
    transcripts_path = args.transcripts_path or DEFAULT_TRANSCRIPTS_PATH

    if not target.startswith("http"):
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

    cache = load_transcript_cache(transcripts_path)
    if os.path.exists(transcripts_file):
        cache.update(load_transcript_cache(transcripts_file))

    entries = get_video_entries(profile_url)

    if not entries:
        print("No videos found. Check the profile URL.")
        sys.exit(1)

    if limit and limit > 0:
        entries = entries[:limit]

    print(f"Found {len(entries)} videos. Loading Whisper model...")

    model, device = load_whisper_model("small.en")
    if device == "cuda":
        print("Using GPU acceleration (CUDA)")
    elif device == "mps":
        print("Using Apple MPS acceleration")
    else:
        print("Using CPU (slow)")

    with open(transcripts_file, "w", encoding="utf-8") as f:
        f.write(f"# TikTok Transcripts for {username}\n\n")

    for idx, entry in enumerate(entries):
        video_url = entry.get('url') or entry.get('webpage_url')
        if not video_url:
            continue

        title = entry.get('title', f"Video {idx+1}")

        video_id = extract_video_id(video_url)
        if video_id and video_id in cache:
            print(f"\n[{idx+1}/{len(entries)}] [CACHE HIT] Loading: {title}")
            transcript = cache[video_id]
            with open(transcripts_file, "a", encoding="utf-8") as f:
                f.write(f"## {title}\nURL: {video_url}\n\n{transcript}\n\n")
            continue

        print(f"\n[{idx+1}/{len(entries)}] Transcribing: {title}")
        audio_path = f"tmp_audio_{idx}.mp3"
        try:
            download_audio(video_url, audio_path)
            transcript = transcribe_audio(model, audio_path)

            with open(transcripts_file, "a", encoding="utf-8") as f:
                f.write(f"## {title}\nURL: {video_url}\n\n{transcript}\n\n")

            append_to_transcripts_file(transcripts_path, title, video_url, transcript)
            if video_id:
                cache[video_id] = transcript
        except Exception as e:
            print(f"Error on video {idx+1}: {e}")
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    print("All videos transcribed successfully.")

    summarize_transcripts(transcripts_file, summaries_file)
    cleanup_temp_files()
    print(f"\nProcess complete! Results saved in {output_dir}/")


if __name__ == "__main__":
    main()
