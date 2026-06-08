import re

def extract_suggestions(text):
    # Split into sentences roughly
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    
    suggestion_keywords = ['recommend', 'take', 'taking', 'stack', 'mg', 'mcg', 'peptide', 'use', 'using', 'start', 'stop', 'diet', 'eat', 'fast', 'workout', 'train', 'add', 'try']
    
    suggestions = []
    first_sentence = sentences[0] if len(sentences) > 0 else ""
    
    for sentence in sentences[1:]:
        if any(kw in sentence.lower() for kw in suggestion_keywords):
            suggestions.append(sentence.strip())
            
    # If we have too many suggestions, keep the most important looking ones or just the first 2-3
    if len(suggestions) > 3:
        suggestions = suggestions[:3]
        
    if not suggestions:
        # If no explicit suggestions found, just take the second sentence to give more context than the previous script
        if len(sentences) > 1:
            suggestions.append(sentences[1].strip())
        else:
            suggestions.append("Mentions a protocol but no explicit instructions given.")
            
    return first_sentence, suggestions

def main():
    with open('/Users/denis/.gemini/antigravity-ide/scratch/tiktok_summarizer/substantive_videos.txt', 'r', encoding='utf-8') as f:
        content = f.read()

    blocks = content.split('==================================================')
    
    with open('/Users/denis/.gemini/antigravity-ide/brain/1b237685-ae09-418a-bbe9-4aee47dd0d72/detailed_video_summaries.md', 'w', encoding='utf-8') as out:
        out.write('# Detailed Video Protocols & Suggestions\n\n')
        out.write('This document highlights the specific recommendations, peptides, and protocols discussed in each substantive video.\n\n')
        
        for block in blocks:
            block = block.strip()
            if not block:
                continue
                
            lines = block.split('\n')
            title = lines[0].replace('Title: ', '').strip()
            url = lines[1].replace('URL: ', '').strip()
            transcript = " ".join(lines[2:]).replace('Transcript: ', '').strip()
            
            # Clean up the transcript string a bit
            transcript = re.sub(r'\s+', ' ', transcript)
            
            first_sentence, suggestions = extract_suggestions(transcript)
            
            out.write(f"### [{title}]({url})\n")
            out.write(f"**Topic**: {first_sentence}\n\n")
            out.write("**Key Suggestions / Takeaways**:\n")
            for sug in suggestions:
                # Highlight keywords
                for kw in ['peptide', 'stack', 'mg', 'mcg', 'diet', 'fasting', 'testosterone', 'melanotan', 'bpc', 'tb500', 'semax', 'selank', 'ghk', 'kpv', 'mots', 'ss-31', 'glutathione', 'nad+', 'dim', 'epitalon']:
                    # case insensitive replacement to make it bold
                    pattern = re.compile(re.escape(kw), re.IGNORECASE)
                    sug = pattern.sub(f"**{kw.upper()}**", sug)
                    
                out.write(f"- {sug}\n")
            out.write("\n")

if __name__ == "__main__":
    main()
