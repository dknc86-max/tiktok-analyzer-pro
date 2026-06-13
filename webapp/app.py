"""
Flask web application for TikTok Analyzer Pro.
Serves the web dashboard and API endpoints.
"""

from flask import Flask, render_template, request, jsonify
from logger import get_logger
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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

        if not target:
            logger.warning("Analysis request with no target")
            return jsonify({"error": "Target is required"}), 400

        logger.info(f"Starting analysis for: {target}")
        job_id = start_analysis(target, api_key=api_key, max_videos=max_videos)
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


@app.route("/api/config", methods=["GET"])
def get_config():
    """
    Get non-sensitive configuration info.
    
    Returns public configuration like model names, ports, etc.
    """
    return jsonify(
        {
            "whisper_model": config.WHISPER_MODEL,
            "flask_port": config.FLASK_PORT,
            "flask_host": config.FLASK_HOST,
            "gemini_model": config.GEMINI_MODEL,
            "has_gemini_key": bool(config.GEMINI_API_KEY),
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
