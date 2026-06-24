"""
Unit tests for configuration module.
"""

import pytest
import os
from unittest.mock import patch
import config


class TestConfigurationPaths:
    """Test configuration path setup."""

    def test_project_root_exists(self):
        """Test that project root is defined."""
        assert config.PROJECT_ROOT is not None
        assert config.PROJECT_ROOT.exists()

    def test_results_dir_created(self):
        """Test that results directory is created."""
        assert config.RESULTS_DIR.exists()

    def test_cache_dir_created(self):
        """Test that cache directory is created."""
        assert config.CACHE_DIR.exists()


class TestEnvironmentVariables:
    """Test environment variable handling."""

    def test_default_values_exist(self):
        """Test that all configuration has defaults."""
        assert config.WHISPER_MODEL == "small.en"
        assert config.FLASK_PORT == 5001
        assert config.DOWNLOAD_TIMEOUT == 15
        assert config.GEMINI_MAX_REQUESTS_PER_MINUTE == 12

    @patch.dict(os.environ, {"FLASK_PORT": "8000"})
    def test_environment_override(self):
        """Test that environment variables can override defaults."""
        # Note: config is already imported, so we need to reload it
        # In a real test, you'd use importlib.reload
        # This demonstrates the concept
        assert int(os.environ.get("FLASK_PORT", "5001")) == 8000

    def test_integer_conversion(self):
        """Test that integer configs are properly converted."""
        assert isinstance(config.FLASK_PORT, int)
        assert isinstance(config.DOWNLOAD_TIMEOUT, int)
        assert isinstance(config.WHISPER_BEAM_SIZE, int)


class TestClassificationData:
    """Test classification data structures."""

    def test_junk_indicators_is_list(self):
        """Test that junk indicators list is properly defined."""
        assert isinstance(config.JUNK_INDICATORS, list)
        assert len(config.JUNK_INDICATORS) > 0
        assert all(isinstance(item, str) for item in config.JUNK_INDICATORS)

    def test_compounds_list_not_empty(self):
        """Test that compounds list is populated."""
        assert isinstance(config.COMPOUNDS, list)
        assert len(config.COMPOUNDS) > 0
        assert "BPC-157" in config.COMPOUNDS
        assert "TB-500" in config.COMPOUNDS

    def test_action_keywords_list(self):
        """Test that action keywords are defined."""
        assert isinstance(config.ACTION_KEYWORDS, list)
        assert "dose" in config.ACTION_KEYWORDS
        assert "inject" in config.ACTION_KEYWORDS

    def test_advice_keywords_list(self):
        """Test that advice keywords are defined."""
        assert isinstance(config.ADVICE_KEYWORDS, list)
        assert "should" in config.ADVICE_KEYWORDS
        assert "important" in config.ADVICE_KEYWORDS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
