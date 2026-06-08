import os
import glob
import re

def clean_vtt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Skip empty lines, WEBVTT header, and timestamp lines
        if not line or line == 'WEBVTT' or '-->' in line or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        # Remove any HTML-like tags like <c.colorE5E5E5> or <00:00:01.000>
        line = re.sub(r'<[^>]+>', '', line)
        if line and (not cleaned_lines or cleaned_lines[-1] != line):
            cleaned_lines.append(line)
            
    return " ".join(cleaned_lines)

def main():
    vtt_files = glob.glob('subs/*.vtt')
    print(f"Found {len(vtt_files)} transcript files.")
    
    with open('all_transcripts.txt', 'w', encoding='utf-8') as out_f:
        for idx, file_path in enumerate(vtt_files):
            # Extract video info from filename
            filename = os.path.basename(file_path)
            # Remove .en.vtt or similar extensions
            name = filename.rsplit('.', 2)[0]
            
            transcript = clean_vtt(file_path)
            if transcript:
                out_f.write(f"--- Video: {name} ---\n")
                out_f.write(transcript + "\n\n")
            
    print("Consolidated transcripts into all_transcripts.txt")

if __name__ == "__main__":
    main()
