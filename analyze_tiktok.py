import os
import sys
import argparse
import signal
import glob
import yat
import requests
from typing import Optional

from core import (
    get_video_entries, download_audio, normalize_transcript, classify_video,
    extract_suggestions, extract_video_id, load_transcript_cache,
    append_to_transcripts_file, USE_FASTER, WhisperModel,
    load_whisper_model, video_hash, save_srt, save_vtt,
    extract_fallback_protocols, check_interactions, COMPOUNDS,
    load_job_state, save_job_state, is_in_state, transcribe_audio,
    load_config, write_protocols_csv, write_protocols_json
)

DEFAULT_TRANSCRIPTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "transcripts.md"
)


def _detect_source(target):
    if target.startswith("http"):
        if "youtube.com" in target or "youtu.be" in target:
            return "youtube"
    return "tiktok"


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
            topic, suggestions, protocols = extract_suggestions(transcript, category, return_protocols=True)

            out.write(f"### [{title}]({url})\n")
            out.write(f"**Topic**: {topic}\n\n")
            out.write("**Key Suggestions / Takeaways**:\n")
            for sug in suggestions:
                out.write(f"- {sug}\n")
            if protocols:
                out.write("\n**Structured Protocols**:\n")
                for p in protocols:
                    dose = p.get('dose', 'N/A')
                    timing = p.get('timing', 'N/A')
                    route = p.get('route', 'N/A')
                    conf = p.get('confidence', 'low')
                    out.write(f"- **{p['compound']}**: {dose} | {timing} | {route} | confidence: {conf}\n")
            out.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Download, transcribe, and summarize a TikTok or YouTube profile.")
    parser.add_argument("target", help="TikTok/@username or YouTube URL")
    parser.add_argument("--limit", type=int, default=50, help="Max videos (default: 50, 0 for all)")
    parser.add_argument("--transcripts-path", default=None, help="Path to shared transcripts cache")
    parser.add_argument("--model", default=None, help="Whisper model size (overrides config)")
    parser.add_argument("--source", choices=["tiktok", "youtube"], default=None, help="Content source (auto-detected from URL if omitted)")
    parser.add_argument("--resume", action="store_true", help="Resume from last state file if interrupted")
    parser.add_argument("--export-srt", action="store_true", help="Export .srt subtitle files per video")
    parser.add_argument("--export-vtt", action="store_true", help="Export .vtt subtitle files per video")
    parser.add_argument("--export-csv", action="store_true", help="Export structured protocols to CSV")
    parser.add_argument("--export-json", action="store_true", help="Export structured protocols to JSON")
    parser.add_argument("--check-interactions", action="store_false", help="Disable compound interaction checks (enabled by default)")
    parser.add_argument("--no-vad", action="store_true", help="Disable VAD filtering")
    args = parser.parse_args()

    config = load_config()
    transcripts_path = args.transcripts_path or DEFAULT_TRANSCRIPTS_PATH
    model_name = str(args.model or config.get("model", "small.en"))

    target = args.target
    limit = args.limit
    source = args.source or _detect_source(target)

    if not target.startswith("http"):
        if source == "youtube":
            profile_url = f"https://www.youtube.com/@{target.lstrip('@')}"
            username = target if target.startswith("@") else f"@{target}"
        else:
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
    state_file = os.path.join(output_dir, "job_state.json")

    state = load_job_state(state_file) if args.resume else {"completed": [], "failed": [], "skipped": [], "last_idx": -1}

    cache = load_transcript_cache(transcripts_path)
    if os.path.exists(transcripts_file):
        cache.update(load_transcript_cache(transcripts_file))

    entries = get_video_entries(profile_url, source=source)

    if not entries:
        print("No videos found. Check the profile URL.")
        sys.exit(1)

    if limit and limit > 0:
        entries = entries[:limit]

    print(f"Found {len(entries)} videos. Loading Whisper model...")

    model, device = load_whisper_model(model_name)
    if device == "cuda":
        print("Using GPU acceleration (CUDA)")
    elif device == "mps":
        print("Using Apple MPS acceleration")
    else:
        print("Using CPU (slow)")

    with open(transcripts_file, "w", encoding="utf-8") as f:
        f.write(f"# TikTok Transcripts for {username}\n\n")

    seen_hashes = set()
    all_protocols = []
    all_compounds = set()

    for idx, entry in enumerate(entries):
        if idx <= state.get("last_idx", -1):
            continue

        video_url = entry.get('url') or entry.get('webpage_url')
        if not video_url:
            continue

        title = entry.get('title', f"Video {idx+1}")
        vhash = video_hash(video_url, title)

        if vhash in seen_hashes:
            print(f"\n[{idx+1}/{len(entries)}] [DEDUP SKIP] Duplicate: {title}")
            state["skipped"].append(extract_video_id(video_url) or vhash)
            continue
        seen_hashes.add(vhash)

        video_id = extract_video_id(video_url)
        if video_id and video_id in cache:
            print(f"\n[{idx+1}/{len(entries)}] [CACHE HIT] Loading: {title}")
            transcript = cache[video_id]
            with open(transcripts_file, "a", encoding="utf-8") as f:
                f.write(f"## {title}\nURL: {video_url}\n\n{transcript}\n\n")
            state["completed"].append(video_id)
            state["last_idx"] = idx
            save_job_state(state_file, state)

            category = classify_video(transcript, title)
            _, _, protocols = extract_suggestions(transcript, category, return_protocols=True)
            if protocols:
                all_protocols.extend(protocols)
                for p in protocols:
                    all_compounds.add(p.get('compound', ''))
            continue

        print(f"\n[{idx+1}/{len(entries)}] Transcribing: {title}")
        audio_path = f"tmp_audio_{idx}.mp3"
        try:
            download_audio(video_url, audio_path)
            language = None  # auto-detect
            if args.no_vad:
                language = "en"
            text, segments, _ = transcribe_audio(model, audio_path, return_segments=True, language=language)
            transcript = text

            with open(transcripts_file, "a", encoding="utf-8") as f:
                f.write(f"## {title}\nURL: {video_url}\n\n{transcript}\n\n")

            if args.export_srt:
                srt_path = os.path.join(output_dir, f"{idx+1:03d}_{title[:40].replace('/', '_')}.srt")
                save_srt(segments, srt_path)

            if args.export_vtt:
                vtt_path = os.path.join(output_dir, f"{idx+1:03d}_{title[:40].replace('/', '_')}.vtt")
                save_vtt(segments, vtt_path)

            append_to_transcripts_file(transcripts_path, title, video_url, transcript)
            if video_id:
                cache[video_id] = transcript

            category = classify_video(transcript, title)
            _, _, protocols = extract_suggestions(transcript, category, return_protocols=True)
            if protocols:
                all_protocols.extend(protocols)
                for p in protocols:
                    all_compounds.add(p.get('compound', ''))

            state["completed"].append(video_id or vhash)
            state["last_idx"] = idx
            save_job_state(state_file, state)

        except Exception as e:
            print(f"Error on video {idx+1}: {e}")
            state["failed"].append(video_id or vhash)
            state["last_idx"] = idx
            save_job_state(state_file, state)
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    print("\nAll videos transcribed successfully.")

    if args.check_interactions and all_compounds:
        print("\n=== Interaction Warnings ===")
        warnings = check_interactions(list(all_compounds))
        for w in warnings:
            print(f"- {', '.join(w['compounds'])}: {w['message']}")

    summarize_transcripts(transcripts_file, summaries_file)
    cleanup_temp_files()
    print(f"\nProcess complete! Results saved in {output_dir}/")


if __name__ == "__main__":
    main()
