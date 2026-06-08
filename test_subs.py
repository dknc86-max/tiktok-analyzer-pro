import json
import subprocess
import requests

def get_subs(url):
    print(f"Dumping JSON for {url}")
    result = subprocess.run(
        ['./venv/bin/yt-dlp', '--dump-json', url], 
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print("Failed to run yt-dlp")
        return
        
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Failed to parse JSON")
        return
        
    subtitles = data.get('subtitles', {})
    if not subtitles:
        print("No subtitles found in metadata.")
        return
        
    for lang, subs_list in subtitles.items():
        if subs_list:
            sub_url = subs_list[0]['url']
            print(f"Found subtitle URL for {lang}: {sub_url[:50]}...")
            
            # Download the subtitle
            r = requests.get(sub_url)
            if r.status_code == 200:
                with open(f"sub_test_{lang}.vtt", 'wb') as f:
                    f.write(r.content)
                print(f"Saved sub_test_{lang}.vtt")
            else:
                print(f"Failed to download. Status code: {r.status_code}")
            return

get_subs("https://www.tiktok.com/@jacobnach/video/7647575950921714975")
