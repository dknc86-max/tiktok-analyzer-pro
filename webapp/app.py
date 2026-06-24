"""
Flask web application for TikTok Analyzer Pro.
Serves the web dashboard and API endpoints.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, render_template, request, jsonify
from logger import get_logger
from analyzer import start_analysis, get_job_status
import config

logger = get_logger("webapp")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@app.route("/")
def index():
    """Serve the main web interface."""
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Start analysis of a TikTok profile.
    
    Expected JSON:
    {
        "target": "@username or URL",
        "api_key": "optional Gemini API key",
        "max_videos": 50
    }
    """
    try:
        data = request.json or {}
        target = data.get("target", "").strip()
        api_key = data.get("api_key", "").strip() or config.GEMINI_API_KEY
        max_videos = data.get("max_videos", 50)
        force_refresh = data.get("force_refresh", False)

        if not target:
            logger.warning("Analysis request with no target")
            return jsonify({"error": "Target is required"}), 400

        logger.info(f"Starting analysis for: {target} (force_refresh={force_refresh})")
        job_id = start_analysis(target, api_key=api_key, max_videos=max_videos, force_refresh=force_refresh)
        return jsonify({"job_id": job_id})
    except Exception as e:
        logger.error(f"Error in /analyze: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/status/<job_id>", methods=["GET"])
def status(job_id):
    """
    Get status of an analysis job.
    
    Returns job progress and status information.
    """
    try:
        status_data = get_job_status(job_id)
        return jsonify(status_data)
    except Exception as e:
        logger.error(f"Error getting status for {job_id}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/synthesize", methods=["POST"])
def synthesize():
    """
    Synthesize master protocols from all transcripts.
    
    Expected JSON:
    {
        "api_key": "optional Gemini API key"
    }
    """
    try:
        data = request.json or {}
        api_key = data.get("api_key", "").strip() or config.GEMINI_API_KEY

        input_file = str(config.TRANSCRIPTS_FILE)

        if not os.path.exists(input_file):
            logger.warning(f"Transcripts file not found: {input_file}")
            return (
                jsonify({"error": "No transcripts found. Please analyze a profile first."}),
                404,
            )

        logger.info("Starting synthesis of master protocols")

        from synthesize_protocols import (
            parse_transcripts,
            classify_video,
            HAS_GENAI,
            genai,
            synthesize_category_with_gemini,
            synthesize_offline,
        )

        videos = parse_transcripts(input_file)
        if not videos:
            logger.warning("No transcripts found to synthesize")
            return jsonify({"error": "No transcripts found to synthesize."}), 404

        client = None
        if HAS_GENAI and api_key:
            try:
                client = genai.Client(api_key=api_key)
                logger.info("Using Gemini API for synthesis")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini client: {e}")
                client = None

        if client:
            categories = {}
            for v in videos:
                cat = classify_video(v["transcript"])
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
            logger.info("Using offline synthesis")
            md = synthesize_offline(videos)

        logger.info("Synthesis complete")
        return jsonify({"markdown": md})
    except Exception as e:
        logger.error(f"Error in /synthesize: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def find_relevant_context(message: str, results: list, max_chars: int = 15000) -> str:
    """
    Find relevant transcript segments based on keywords in the message.
    """
    import re
    keywords = re.findall(r'\b\w{4,15}\b', message.lower())
    if not keywords:
        context_parts = []
        current_len = 0
        for item in results:
            part = f"Video: {item['title']}\nTranscript: {item['transcript']}\n"
            if current_len + len(part) > max_chars:
                break
            context_parts.append(part)
            current_len += len(part)
        return "\n".join(context_parts)
        
    scored_items = []
    for item in results:
        text = (item['title'] + " " + item['transcript'] + " " + " ".join(item['suggestions'])).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored_items.append((score, item))
            
    scored_items.sort(key=lambda x: x[0], reverse=True)
    
    if not scored_items:
        scored_items = [(0, item) for item in results]
        
    context_parts = []
    current_len = 0
    for _, item in scored_items:
        part = f"Video: {item['title']}\nCategory: {item['category']}\nTakeaways: {', '.join(item['suggestions'])}\nTranscript: {item['transcript']}\n"
        if current_len + len(part) > max_chars:
            if context_parts:
                break
        context_parts.append(part)
        current_len += len(part)
        
    return "\n".join(context_parts)


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Chat with a creator's transcribed protocols using Gemini or offline fallback.
    """
    try:
        data = request.json or {}
        message = data.get("message", "").strip()
        job_id = data.get("job_id", "").strip()
        api_key = data.get("api_key", "").strip() or config.GEMINI_API_KEY
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        if not job_id:
            return jsonify({"error": "Job ID is required"}), 400
            
        status_data = get_job_status(job_id)
        if status_data.get("status") == "not_found":
            return jsonify({"error": "Job not found. Please analyze a profile first."}), 404
        if status_data.get("status") != "completed":
            return jsonify({"error": "Analysis is still in progress. Please wait until it completes."}), 400
            
        results = status_data.get("results", [])
        if not results:
            return jsonify({"error": "No transcripts available for this profile."}), 400
            
        context = find_relevant_context(message, results)
        
        from synthesize_protocols import HAS_GENAI, genai
        
        client = None
        if HAS_GENAI and api_key:
            try:
                client = genai.Client(api_key=api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Gemini client for chat: {e}")
                client = None
                
        if client:
            prompt = f"""You are an expert AI health and routine assistant. Your task is to answer the user's question by reference ONLY to the provided creator video transcripts, topics, and suggestions. 
            
Do not make up facts or protocols that are not discussed in the transcripts. Be concise, objective, and reference the specific videos by title when mentioning their recommendations.

Provided Transcripts and Routine Context:
{context}

User's Question: "{message}"
"""
            response = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
            )
            reply = response.text.strip()
        else:
            import re
            keywords = re.findall(r'\b\w{4,15}\b', message.lower())
            matched_bullets = []
            for item in results:
                for sug in item["suggestions"]:
                    if any(kw in sug.lower() for kw in keywords):
                        matched_bullets.append(f"- {sug} (from \"{item['title']}\")")
            if matched_bullets:
                reply = "*(Offline Mode)* Here are the relevant matching protocols found in the transcripts:\n\n" + "\n".join(matched_bullets[:8])
            else:
                reply = "*(Offline Mode)* I couldn't find any direct matches for your question. Here is a summary of the creator's top recommendations:\n\n"
                all_bullets = []
                for item in results[:3]:
                    all_bullets.append(f"**From \"{item['title']}\":**")
                    all_bullets.extend(f"- {sug}" for sug in item["suggestions"][:2])
                reply += "\n".join(all_bullets)
                
        return jsonify({"reply": reply})
    except Exception as e:
        logger.error(f"Error in /chat: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/config", methods=["GET"])
def get_config():
    """
    Get non-sensitive configuration info.
    
    Returns public configuration like model names, ports, and dynamic concepts.
    """
    return jsonify(
        {
            "whisper_model": config.WHISPER_MODEL,
            "flask_port": config.FLASK_PORT,
            "flask_host": config.FLASK_HOST,
            "gemini_model": config.GEMINI_MODEL,
            "has_gemini_key": bool(config.GEMINI_API_KEY),
            "compounds": config.COMPOUNDS,
            "action_keywords": config.ACTION_KEYWORDS,
            "advice_keywords": config.ADVICE_KEYWORDS,
            "junk_indicators": config.JUNK_INDICATORS,
            "skip_intros": config.SKIP_INTROS,
        }
    )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    logger.error(f"Server error: {error}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    logger.info(
        f"Starting Flask app on {config.FLASK_HOST}:{config.FLASK_PORT} (debug={config.FLASK_DEBUG})"
    )
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
