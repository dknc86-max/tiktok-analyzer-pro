"""
Unit tests for core.py functionality.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from core import (
    normalize_transcript,
    classify_video,
    extract_video_id,
    generate_topic_summary,
    extract_fallback_bullets,
)


class TestNormalizeTranscript:
    """Test transcript normalization."""

    def test_normalize_peptide_names(self):
        """Test normalization of common peptide names."""
        assert "Pinealon" in normalize_transcript("penny a lan")
        assert "Epitalon" in normalize_transcript("epitale on")
        assert "BPC-157" in normalize_transcript("BPC 157")
        assert "MOTS-c" in normalize_transcript("mott c")

    def test_normalize_glp1_names(self):
        """Test normalization of GLP1 drug names."""
        assert "Retatrutide" in normalize_transcript("red end")
        assert "Semaglutide" in normalize_transcript("semaglutide")

    def test_preserve_normal_text(self):
        """Test that normal text is preserved."""
        text = "This is a normal sentence about peptides"
        result = normalize_transcript(text)
        assert "normal sentence" in result
        assert "peptides" in result


class TestClassifyVideo:
    """Test video classification logic."""

    def test_classify_short_transcript(self):
        """Short transcripts should be classified as general_advice."""
        assert classify_video("short", "title") == "general_advice"

    def test_classify_peptide_protocol(self):
        """Test classification of peptide protocol videos."""
        transcript = (
            "Today we're discussing the BPC-157 and TB-500 stack protocol. "
            "This is a comprehensive peptide protocol with specific phases and recommendations."
        )
        result = classify_video(transcript, "Peptide Protocol")
        assert result == "peptide_protocol"

    def test_classify_peptide_info(self):
        """Test classification of peptide info videos."""
        transcript = (
            "BPC-157 is a commonly used peptide. It has many potential benefits. "
            "People use it for recovery and healing."
        ) * 5
        result = classify_video(transcript, "Peptide Info")
        assert result == "peptide_info"

    def test_classify_glp1_fat_loss(self):
        """Test classification of GLP1 fat loss videos."""
        transcript = (
            "Semaglutide and tirzepatide are powerful GLP1 agonists. "
            "Let's discuss their use for fat loss and metabolic health."
        ) * 5
        result = classify_video(transcript, "GLP1")
        assert result == "glp1_fat_loss"

    def test_classify_hormones(self):
        """Test classification of hormone videos."""
        transcript = (
            "Testosterone replacement therapy and estrogen management. "
            "Clomiphene and TRT protocols for hormone optimization."
        ) * 5
        result = classify_video(transcript, "Hormones")
        assert result == "hormones"

    def test_classify_nutrition(self):
        """Test classification of nutrition videos."""
        transcript = (
            "Intermittent fasting and protein intake are crucial. "
            "We need to discuss macros and caloric surplus for muscle gain."
        ) * 5
        result = classify_video(transcript, "Nutrition")
        assert result == "nutrition"


class TestExtractVideoId:
    """Test video ID extraction."""

    def test_extract_video_id_from_standard_url(self):
        """Test extraction from standard TikTok URL."""
        url = "https://www.tiktok.com/@creator/video/1234567890123456"
        video_id = extract_video_id(url)
        assert video_id == "1234567890123456"

    def test_extract_video_id_from_long_number(self):
        """Test extraction of long video ID number."""
        url = "https://vm.tiktok.com/something/7123456789012345"
        video_id = extract_video_id(url)
        assert video_id is not None
        assert len(video_id) >= 18

    def test_extract_video_id_returns_none_for_invalid_url(self):
        """Test that invalid URLs return None."""
        assert extract_video_id("not a url") is None
        assert extract_video_id("https://example.com") is None


class TestGenerateTopicSummary:
    """Test topic summary generation."""

    def test_skip_intro_phrases(self):
        """Test that intro phrases are skipped."""
        transcript = (
            "Welcome back everyone! Today we're discussing peptides. "
            "This is a really important topic for anyone interested in optimization."
        )
        summary = generate_topic_summary(transcript)
        assert "peptides" in summary.lower() or "important" in summary.lower()
        assert "welcome" not in summary.lower()

    def test_max_length_truncation(self):
        """Test that summaries are truncated to max length."""
        long_sentence = "This is a very long sentence that should be truncated. " * 10
        summary = generate_topic_summary(long_sentence)
        assert len(summary) <= 120


class TestExtractFallbackBullets:
    """Test fallback bullet point extraction."""

    def test_extract_compounds_found(self):
        """Test extraction of compound mentions."""
        transcript = (
            "Today we're discussing BPC-157 and TB-500. These are powerful peptides. "
            "Take TB-500 for recovery and BPC-157 for healing. This stack is effective."
        )
        bullets = extract_fallback_bullets(transcript, "peptide_protocol")
        bullets_text = " ".join(bullets)
        assert "BPC-157" in bullets_text or "TB-500" in bullets_text

    def test_extract_protocol_sentences(self):
        """Test extraction of protocol-related sentences."""
        transcript = (
            "The recommended dose is 500mcg daily. Inject subcutaneously in the morning. "
            "Stack this with TB-500 for enhanced recovery. Cycle for 8 weeks then take 2 weeks off."
        ) * 3
        bullets = extract_fallback_bullets(transcript, "peptide_protocol")
        assert len(bullets) > 0

    def test_fallback_bullets_returns_list(self):
        """Test that fallback always returns a list."""
        result = extract_fallback_bullets("test", "category")
        assert isinstance(result, list)


class TestImportDependencies:
    """Test that dependencies can be imported."""

    def test_yt_dlp_available(self):
        """Test that yt_dlp is available."""
        import yt_dlp
        assert yt_dlp is not None

    def test_faster_whisper_available(self):
        """Test that faster_whisper is available or handled gracefully."""
        try:
            from faster_whisper import WhisperModel
            assert WhisperModel is not None
        except ImportError:
            # Should gracefully handle missing dependency
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
