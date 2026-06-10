import os
import re
import sys
import glob
import signal
import threading
import yt_dlp
import warnings
from queue import Queue

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core import (
    download_audio, get_video_entries, transcribe_audio, normalize_transcript,
    classify_video, extract_gemini_bullets, extract_fallback_bullets,
    generate_topic_summary, extract_suggestions, extract_video_id,
    load_transcript_cache, append_to_transcripts_file, HAS_GENAI,
    USE_FASTER, WhisperModel, load_whisper_model, video_hash,
    extract_fallback_protocols, check_interactions, COMPOUNDS,
    load_job_state, save_job_state, is_in_state, save_srt, save_vtt
)

warnings.filterwarnings("ignore")

DEFAULT_TRANSCRIPTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'transcripts.md'
)


def cleanup_temp_files():
    pattern = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp_audio_*.mp3')
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

    transcripts_path = DEFAULT_TRANSCRIPTS_PATH
    state_path = os.path.splitext(transcripts_path)[0] + f"_{job_id}_state.json"

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
            jobs[job_id]["status"] = "error"
            jobs[job_id]["message"] = "No videos found. Check the profile URL."
            return

        if max_videos and max_videos > 0:
            entries = entries[:max_videos]

        total_videos = len(entries)
        jobs[job_id]["total"] = total_videos
        jobs[job_id]["status"] = "transcribing"
        jobs[job_id]["message"] = f"Found {total_videos} videos. Loading AI model..."

        cache = load_transcript_cache(transcripts_path)
        state = load_job_state(state_path)
        seen_hashes = set()

        model, device = load_whisper_model("small.en")

        extracted_data = []
        all_compounds = set()

        download_queue = Queue(maxsize=2)

        def prefetch_worker():
            for idx, entry in enumerate(entries):
                video_url = entry.get('url') or entry.get('webpage_url')
                if not video_url:
                    download_queue.put(None)
                    continue
                title = entry.get('title', f"Video {idx+1}")

                video_id = extract_video_id(video_url)
                if video_id and video_id in cache:
                    download_queue.put((idx, title, video_url, None, cache[video_id]))
                    continue

                vhash = video_hash(video_url, title)
                if vhash in seen_hashes:
                    download_queue.put((idx, title, video_url, None, None, "dedup"))
                    continue
                seen_hashes.add(vhash)

                audio_path = f"tmp_audio_{job_id}_{idx}.mp3"
                try:
                    download_audio(video_url, audio_path)
                    download_queue.put((idx, title, video_url, audio_path, None, "ok"))
                except Exception:
                    download_queue.put((idx, title, video_url, None, None, "error"))
            download_queue.put("DONE")

        prefetch_thread = threading.Thread(target=prefetch_worker, daemon=True)
        prefetch_thread.start()

        while True:
            item = download_queue.get()

            if item == "DONE":
                break

            if item is None:
                jobs[job_id]["progress"] = jobs[job_id].get("progress", 0) + 1
                continue

            idx, title, video_url, audio_path, cached_transcript, status = item if len(item) == 6 else (*item, "ok")
            jobs[job_id]["progress"] = idx + 1
            jobs[job_id]["current_video"] = title

            try:
                if status == "dedup":
                    jobs[job_id]["message"] = f"⏭ Skipping duplicate video {idx+1} of {total_videos}..."
                    state["skipped"].append(extract_video_id(video_url) or video_hash(video_url, title))
                    save_job_state(state_path, state)
                    continue

                if cached_transcript is not None:
                    jobs[job_id]["message"] = f"⚡ Loading cached transcript for video {idx+1} of {total_videos}..."
                    transcript = cached_transcript
                    segments = []
                else:
                    jobs[job_id]["message"] = f"⚡ Transcribing video {idx+1} of {total_videos}..."
                    transcript, segments, _ = transcribe_audio(model, audio_path, return_segments=True, language=None)
                    append_to_transcripts_file(transcripts_path, title, video_url, transcript)

                transcript = re.sub(r'\s+', ' ', transcript)

                if len(transcript) > 150 and "song" not in transcript.lower():
                    category = classify_video(transcript, title)
                    topic, suggestions, protocols = extract_suggestions(transcript, category, api_key, return_protocols=True)

                    if not protocols:
                        protocols = extract_fallback_protocols(transcript)

                    video_compounds = [p.get('compound', '') for p in protocols if p.get('compound')]
                    all_compounds.update(video_compounds)
                    warnings_list = check_interactions(video_compounds)

                    result_item = {
                        "title": title,
                        "url": video_url,
                        "topic": topic,
                        "category": category,
                        "suggestions": suggestions,
                        "transcript": transcript,
                        "protocols": protocols,
                        "interaction_warnings": warnings_list,
                        "segments": segments if segments else []
                    }
                    extracted_data.append(result_item)

                video_id = extract_video_id(video_url)
                state["completed"].append(video_id or video_hash(video_url, title))
                state["last_idx"] = idx
                save_job_state(state_path, state)

            except Exception as e:
                print(f"Error on video {idx+1}: {e}")
                state["failed"].append(extract_video_id(video_url) or video_hash(video_url, title))
                state["last_idx"] = idx
                save_job_state(state_path, state)
            finally:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)

        prefetch_thread.join()

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["message"] = "Analysis complete!"
        jobs[job_id]["results"] = extracted_data

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["message"] = str(e)


def start_analysis(target, api_key=None, max_videos=50):
    job_id = re.sub(r'[^a-zA-Z0-9]', '_', target.lower())

    if job_id not in jobs or jobs[job_id]["status"] in ["completed", "error"]:
        thread = threading.Thread(target=analyze_profile_background, args=(job_id, target, api_key, max_videos))
        thread.start()

    return job_id


def get_job_status(job_id):
    return jobs.get(job_id, {"status": "not_found", "message": "Job not found"})
