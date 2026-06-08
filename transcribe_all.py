import os
import sys
import imageio_ffmpeg

# Inject ffmpeg binary into PATH for Whisper
local_bin = os.path.abspath("local_bin")
os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")

import whisper
import yt_dlp
import warnings
from tqdm import tqdm

warnings.filterwarnings("ignore")

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
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

def main():
    profile_url = "https://www.tiktok.com/@jacobnach"
    entries = get_video_entries(profile_url)
    
    print(f"Found {len(entries)} videos. Loading Whisper model...")
    model = whisper.load_model("tiny.en") # Use tiny.en for maximum speed
    
    output_file = "transcripts.md"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# TikTok Transcripts\n\n")
        
    for idx, entry in enumerate(tqdm(entries, desc="Transcribing Videos")):
        video_url = entry.get('url') or entry.get('webpage_url')
        if not video_url:
            continue
            
        title = entry.get('title', f"Video {idx+1}")
        tqdm.write(f"\n[{idx+1}/{len(entries)}] Processing: {title}")
        
        audio_path = f"tmp_audio_{idx}.mp3"
        try:
            # 1. Download
            download_audio(video_url, audio_path)
            
            # 2. Transcribe
            result = model.transcribe(audio_path)
            transcript = result["text"].strip()
            
            # 3. Save
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(f"## {title}\nURL: {video_url}\n\n{transcript}\n\n")
                
        except Exception as e:
            tqdm.write(f"Error on video {idx+1}: {e}")
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                
    print("All videos transcribed successfully.")

if __name__ == "__main__":
    main()
