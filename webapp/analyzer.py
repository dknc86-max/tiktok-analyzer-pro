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
    USE_FASTER, WhisperModel, load_whisper_model
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

        model, device = load_whisper_model("small.en")

        extracted_data = []

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

        while True:
            item = download_queue.get()

            if item == "DONE":
                break

            if item is None:
                jobs[job_id]["progress"] = jobs[job_id].get("progress", 0) + 1
                continue

            idx, title, video_url, audio_path, cached_transcript = item
            jobs[job_id]["progress"] = idx + 1
            jobs[job_id]["current_video"] = title

            try:
                if cached_transcript is not None:
                    jobs[job_id]["message"] = f"⚡ Loading cached transcript for video {idx+1} of {total_videos}..."
                    transcript = cached_transcript
                else:
                    jobs[job_id]["message"] = f"⚡ Transcribing video {idx+1} of {total_videos}..."
                    transcript = transcribe_audio(model, audio_path)
                    append_to_transcripts_file(transcripts_path, title, video_url, transcript)

                transcript = re.sub(r'\s+', ' ', transcript)

                if len(transcript) > 150 and "song" not in transcript.lower():
                    category = classify_video(transcript, title)
                    topic, suggestions = extract_suggestions(transcript, category, api_key)

                    extracted_data.append({
                        "title": title,
                        "url": video_url,
                        "topic": topic,
                        "category": category,
                        "suggestions": suggestions,
                        "transcript": transcript
                    })

            except Exception as e:
                print(f"Error on video {idx+1}: {e}")
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
