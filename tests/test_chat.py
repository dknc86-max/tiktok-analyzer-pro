"""
Unit tests for chat functionality in app.py.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Ensure webapp can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../webapp"))

from webapp.app import app, find_relevant_context

class TestChatLogic:
    """Test find_relevant_context helper function."""

    def test_find_relevant_context_no_keywords(self):
        """Test fallback when no keywords are matched or present."""
        results = [
            {"title": "Video A", "transcript": "some long transcript text here", "suggestions": [], "category": "general_advice"},
            {"title": "Video B", "transcript": "another transcript text", "suggestions": [], "category": "general_advice"},
        ]
        context = find_relevant_context("", results)
        assert "Video A" in context
        assert "Video B" in context

    def test_find_relevant_context_with_keywords(self):
        """Test filtering context based on message keywords."""
        results = [
            {
                "title": "Sleep Protocol",
                "transcript": "In this video we talk about magnesium threonate for sleep quality.",
                "suggestions": ["magnesium for sleep"],
                "category": "peptide_protocol"
            },
            {
                "title": "BPC 157 Guide",
                "transcript": "Let's review the BPC-157 healing dosage for gut and joints.",
                "suggestions": ["inject BPC-157"],
                "category": "peptide_info"
            }
        ]
        # Searching for sleep keyword
        context = find_relevant_context("What about sleep?", results)
        assert "Sleep Protocol" in context
        assert "BPC 157 Guide" not in context

    def test_find_relevant_context_keyword_fallback(self):
        """Test fallback to all results when keywords are present but no matches are found."""
        results = [
            {"title": "Video A", "transcript": "text A", "suggestions": [], "category": "general_advice"},
            {"title": "Video B", "transcript": "text B", "suggestions": [], "category": "general_advice"},
        ]
        context = find_relevant_context("unmatchedkeyword", results)
        assert "Video A" in context
        assert "Video B" in context


class TestChatApi:
    """Test /api/chat Flask endpoint."""

    @pytest.fixture
    def client(self):
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_chat_missing_parameters(self, client):
        """Test missing parameters return 400."""
        res = client.post("/api/chat", json={})
        assert res.status_code == 400
        assert "Message is required" in res.get_json()["error"]

        res = client.post("/api/chat", json={"message": "hello"})
        assert res.status_code == 400
        assert "Job ID is required" in res.get_json()["error"]

    @patch("webapp.app.get_job_status")
    def test_chat_job_not_found(self, mock_get_job_status, client):
        """Test when job_id is not found."""
        mock_get_job_status.return_value = {"status": "not_found"}
        res = client.post("/api/chat", json={"message": "hello", "job_id": "invalid-job"})
        assert res.status_code == 404
        assert "Job not found" in res.get_json()["error"]

    @patch("webapp.app.get_job_status")
    def test_chat_job_in_progress(self, mock_get_job_status, client):
        """Test when job is still running."""
        mock_get_job_status.return_value = {"status": "processing"}
        res = client.post("/api/chat", json={"message": "hello", "job_id": "job-123"})
        assert res.status_code == 400
        assert "Analysis is still in progress" in res.get_json()["error"]

    @patch("webapp.app.get_job_status")
    @patch("synthesize_protocols.HAS_GENAI", False)
    def test_chat_offline_fallback(self, mock_get_job_status, client):
        """Test offline fallback response when no Gemini key or package is available."""
        mock_get_job_status.return_value = {
            "status": "completed",
            "results": [
                {
                    "title": "Sleep Stack",
                    "transcript": "Take magnesium threonate 2 hours before bed.",
                    "suggestions": ["magnesium threonate for sleep", "avoid caffeine after 2pm"],
                    "category": "sleep"
                }
            ]
        }
        res = client.post("/api/chat", json={"message": "What magnesium is good?", "job_id": "job-123", "api_key": ""})
        assert res.status_code == 200
        data = res.get_json()
        assert "reply" in data
        assert "Offline Mode" in data["reply"]
        assert "magnesium threonate for sleep" in data["reply"]
