import re

def main():
    with open('transcripts.md', 'r', encoding='utf-8') as f:
        content = f.read()

    videos = content.split('## ')[1:]
    
    substantive_videos = []
    
    for video in videos:
        lines = video.strip().split('\n')
        title = lines[0].strip()
        url = ""
        transcript_lines = []
        
        for line in lines[1:]:
            if line.startswith('URL:'):
                url = line.replace('URL:', '').strip()
            elif line.strip() != '':
                transcript_lines.append(line.strip())
        
        transcript = " ".join(transcript_lines)
        
        # Filter out short videos or videos that are clearly just songs/nonsense
        if len(transcript) > 250 and not "song" in transcript.lower():
            # A rough heuristic: look for keywords like 'peptide', 'stack', 'take', 'protocol', 'recommend', 'body', 'health'
            keywords = ['peptide', 'stack', 'take', 'protocol', 'recommend', 'body', 'health', 'mg', 'mcg', 'dose', 'experiment', 'diet', 'muscle', 'fat']
            if any(kw in transcript.lower() for kw in keywords):
                substantive_videos.append({
                    'title': title,
                    'url': url,
                    'transcript': transcript
                })
                
    print(f"Total substantive videos found: {len(substantive_videos)}")
    
    with open('/Users/denis/.gemini/antigravity-ide/scratch/tiktok_summarizer/substantive_videos.txt', 'w', encoding='utf-8') as out:
        for v in substantive_videos:
            out.write(f"Title: {v['title']}\nURL: {v['url']}\nTranscript: {v['transcript']}\n\n{'='*50}\n\n")

if __name__ == "__main__":
    main()
