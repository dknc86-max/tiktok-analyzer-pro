import re

def summarize(text):
    text = text.strip()
    if not text:
        return "No transcript available."
    
    # Try to grab the first sentence or two.
    # We will just take the first 150 characters and add ... if longer, 
    # but preferably break at a period.
    sentences = re.split(r'(?<=[.!?]) +', text)
    if len(sentences) > 0:
        summary = sentences[0]
        if len(sentences) > 1 and len(summary) < 60:
            summary += " " + sentences[1]
        
        # If it's still too long, truncate it.
        if len(summary) > 200:
            summary = summary[:197] + "..."
        return summary
    return text[:200] + "..." if len(text) > 200 else text

def main():
    with open('transcripts.md', 'r', encoding='utf-8') as f:
        content = f.read()

    videos = content.split('## ')[1:] # skip the first part which is intro
    
    with open('/Users/denis/.gemini/antigravity-ide/brain/1b237685-ae09-418a-bbe9-4aee47dd0d72/video_bullet_points.md', 'w', encoding='utf-8') as out:
        out.write('# TikTok Video Summaries\n\n')
        
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
            
            summary = summarize(transcript)
            
            out.write(f"- **[{title}]({url})**: {summary}\n")

if __name__ == "__main__":
    main()
