from flask import Flask, render_template, request, jsonify
from analyzer import start_analysis, get_job_status, list_jobs, resume_job

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.json
    target = data.get('target')
    api_key = data.get('api_key')
    max_videos = data.get('max_videos', 50)
    target2 = data.get('target2')
    if not target:
        return jsonify({"error": "Target is required"}), 400

    job_id = start_analysis(target, api_key=api_key, max_videos=max_videos)

    comparison_job_id = None
    if target2:
        comparison_job_id = start_analysis(target2, api_key=api_key, max_videos=max_videos)

    return jsonify({"job_id": job_id, "comparison_job_id": comparison_job_id})


@app.route('/api/status/<job_id>', methods=['GET'])
def status(job_id):
    status_data = get_job_status(job_id)
    return jsonify(status_data)

<<<<<<< HEAD
@app.route('/api/jobs', methods=['GET'])
def jobs_list():
    jobs = list_jobs()
    return jsonify(jobs)

@app.route('/api/resume/<job_id>', methods=['POST'])
def resume(job_id):
    resumed = resume_job(job_id)
    if not resumed:
        return jsonify({"error": "Cannot resume this job"}), 400
    return jsonify({"job_id": resumed, "status": "resumed"})

@app.route('/api/dosages/<job_id>', methods=['GET'])
def dosages(job_id):
    status_data = get_job_status(job_id)
    return jsonify(status_data.get("dosages", []))

@app.route('/api/export/obsidian/<job_id>', methods=['GET'])
def export_obsidian(job_id):
    status_data = get_job_status(job_id)
    results = status_data.get("results", [])
    if not results:
        return jsonify({"error": "No results found"}), 404

    md = generate_obsidian_export(results)
    return jsonify({"markdown": md})

@app.route('/api/export/notion/<job_id>', methods=['GET'])
def export_notion(job_id):
    status_data = get_job_status(job_id)
    results = status_data.get("results", [])
    if not results:
        return jsonify({"error": "No results found"}), 404

    md = generate_notion_export(results)
    return jsonify({"markdown": md})

def generate_obsidian_export(results):
    md = "# TikTok Creator Protocols\n\n"
    md += "---\n"
    md += "type: health-protocols\n"
    md += "tags: tiktok, peptides, longevity\n"
    md += "---\n\n"

    categories = {}
    for item in results:
        cat = item.get("category", "general_advice")
        categories.setdefault(cat, []).append(item)

    for cat, items in categories.items():
        md += f"## {cat.replace('_', ' ').title()}\n\n"
        for item in items:
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            topic = item.get("topic", "")
            suggestions = item.get("suggestions", [])

            md += f"### [[{title}]]\n"
            md += f"- **Source**: [{url}]({url})\n"
            md += f"- **Topic**: {topic}\n"
            md += f"- **Category**: `{cat}`\n\n"
            md += "#### Key Takeaways\n"
            for sug in suggestions:
                md += f"- {sug}\n"
            md += "\n"

    return md


def generate_notion_export(results):
    md = "# TikTok Creator Protocols\n\n"
    md += "*Exported for Notion import.*\n\n"
    md += "---\n\n"

    categories = {}
    for item in results:
        cat = item.get("category", "general_advice")
        categories.setdefault(cat, []).append(item)

    for cat, items in categories.items():
        md += f"## {cat.replace('_', ' ').title()}\n\n"
        for item in items:
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            topic = item.get("topic", "")
            suggestions = item.get("suggestions", [])

            md += f"### {title}\n"
            md += f"- **Link**: {url}\n"
            md += f"- **Topic**: {topic}\n\n"
            md += "**Key Takeaways:**\n"
            for sug in suggestions:
                md += f"- {sug}\n"
            md += "\n"

    return md
=======
>>>>>>> origin/main

@app.route('/api/synthesize', methods=['POST'])
def synthesize():
    data = request.json or {}
    api_key = data.get('api_key')

    input_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'transcripts.md'
    )

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
            md += "*Consolidated database analysis of longevity and health protocols (Gemini Premium Mode).*\n\n"
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
