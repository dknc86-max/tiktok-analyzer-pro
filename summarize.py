import argparse
import os
import json
import time
from pathlib import Path
import yt_dlp
from google import genai

def get_video_info(profile_url, limit):
    print(f"Fetching metadata for {profile_url} (limit: {limit})...")
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'dump_single_json': True,
        'playlistend': limit,
        'quiet': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(profile_url, download=False)
        if 'entries' in result:
            return result['entries']
        else:
            return [result]

def download_video(video_url, output_path):
    print(f"Downloading video: {video_url} to {output_path}")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

def wait_for_file_processing(client, file_name):
    print(f"Waiting for video processing on Gemini servers...")
    while True:
        f = client.files.get(name=file_name)
        state_str = str(f.state)
        if 'PROCESSING' in state_str:
            time.sleep(5)
            print(".", end="", flush=True)
        elif 'ACTIVE' in state_str:
            print("\nVideo is ready!")
            break
        elif 'FAILED' in state_str:
            print("\nVideo processing failed.")
            break
        else:
            # Fallback
            break

def summarize_video(client, video_path, video_title, video_url):
    print(f"Uploading {video_path} to Gemini...")
    uploaded_file = client.files.upload(file=video_path)
    
    wait_for_file_processing(client, uploaded_file.name)
    
    print("Generating summary...")
    prompt = "Review this TikTok video. Provide a concise summary of the content using a few bullet points."
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            uploaded_file,
            prompt
        ]
    )
    
    # Clean up the file from Gemini storage
    print("Cleaning up Gemini file...")
    client.files.delete(name=uploaded_file.name)
    
    return response.text

def main():
    parser = argparse.ArgumentParser(description="Summarize TikTok profile videos")
    parser.add_argument("--url", required=True, help="TikTok profile URL")
    parser.add_argument("--limit", type=int, default=5, help="Number of videos to process")
    parser.add_argument("--output", default="summaries.md", help="Output markdown file")
    
    args = parser.parse_args()
    
    try:
        client = genai.Client()
    except Exception as e:
        print(f"Failed to initialize Gemini Client. Make sure GEMINI_API_KEY is set or ADC is configured. Error: {e}")
        return
    
    entries = get_video_info(args.url, args.limit)
    print(f"Found {len(entries)} videos to process.")
    
    tmp_dir = Path("tmp_videos")
    tmp_dir.mkdir(exist_ok=True)
    
    with open(args.output, "a", encoding="utf-8") as f:
        f.write(f"\n# Summaries for {args.url}\n\n")
        
        for idx, entry in enumerate(entries):
            video_url = entry.get('url') or entry.get('webpage_url')
            if not video_url:
                continue
                
            title = entry.get('title', f"Video {idx+1}")
            print(f"\n--- Processing Video {idx+1}/{len(entries)}: {title} ---")
            
            video_path = tmp_dir / f"video_{idx}.mp4"
            
            try:
                # 1. Download
                download_video(video_url, str(video_path))
                
                # 2. Summarize
                summary = summarize_video(client, str(video_path), title, video_url)
                
                # 3. Write to file
                f.write(f"## [{title}]({video_url})\n")
                f.write(f"{summary}\n\n")
                f.flush()
                print("Summary saved.")
                
            except Exception as e:
                print(f"Error processing video {idx+1}: {e}")
            finally:
                # 4. Clean up local file
                if video_path.exists():
                    video_path.unlink()
                    
    print(f"\nAll done! Summaries saved to {args.output}")

if __name__ == "__main__":
    main()
