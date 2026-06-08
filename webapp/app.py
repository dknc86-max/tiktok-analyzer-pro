from flask import Flask, render_template, request, jsonify
from analyzer import start_analysis, get_job_status

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    target = data.get('target')
    api_key = data.get('api_key')
    if not target:
        return jsonify({"error": "Target is required"}), 400
        
    job_id = start_analysis(target, api_key=api_key)
    return jsonify({"job_id": job_id})

@app.route('/api/status/<job_id>', methods=['GET'])
def status(job_id):
    status_data = get_job_status(job_id)
    return jsonify(status_data)

@app.route('/api/synthesize', methods=['POST'])
def synthesize():
    data = request.json or {}
    api_key = data.get('api_key')
    
    # Add project path to python import search path so we can import synthesize_protocols
    import sys
    sys.path.append('/Users/denis/.gemini/antigravity-ide/scratch/tiktok_summarizer')
    
    input_file = '/Users/denis/.gemini/antigravity-ide/scratch/tiktok_summarizer/transcripts.md'
    
    try:
        from synthesize_protocols import parse_transcripts, classify_video, HAS_GENAI, genai, synthesize_category_with_gemini, synthesize_offline
        
        videos = parse_transcripts(input_file)
        if not videos:
            return jsonify({"error": "No transcripts found to synthesize."}), 404
            
        client = None
        if HAS_GENAI and api_key:
            try:
                client = genai.Client(api_key=api_key)
            except Exception:
                client = None
                
        if client:
            categories = {}
            for v in videos:
                cat = classify_video(v['transcript'])
                if cat:
                    if cat not in categories:
                        categories[cat] = []
                    categories[cat].append(v)
                    
            md = "# Synthesized Master Protocols Reference Sheet\n"
            md += "*Consolidated database analysis of @jacobnach's longevity and health experiments (Gemini Premium Mode).*\n\n"
            md += "---\n\n"
            
            for cat, cat_vids in categories.items():
                synthesis = synthesize_category_with_gemini(client, cat, cat_vids)
                if synthesis:
                    md += f"## {cat.replace('_', ' ').title()}\n\n"
                    md += synthesis
                    md += "\n\n---\n\n"
        else:
            md = synthesize_offline(videos)
            
        return jsonify({"markdown": md})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
