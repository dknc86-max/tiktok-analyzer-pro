# Contributing to TikTok Analyzer Pro

Thank you for your interest in contributing to TikTok Analyzer Pro! This document provides guidelines and instructions for contributing.

## Getting Started

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/tiktok-analyzer-pro.git
cd tiktok-analyzer-pro
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-mock mypy black flake8
```

### 3. Configure Environment

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys and preferences
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_core.py

# Run with coverage
pytest --cov=. tests/
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code with Black
black *.py tests/

# Check style with Flake8
flake8 . --max-line-length=100

# Type checking with mypy
mypy *.py
```

### Before Committing

```bash
# 1. Format code
black *.py tests/

# 2. Run tests
pytest

# 3. Check for issues
flake8 . --max-line-length=100
```

## Project Structure

```
tiktok-analyzer-pro/
├── core.py                 # Core scraping and transcription logic
├── config.py               # Centralized configuration
├── logger.py               # Logging setup
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
├── webapp/
│   ├── app.py             # Flask app entry point
│   ├── analyzer.py        # Analysis logic
│   ├── static/            # CSS, JS, images
│   └── templates/         # HTML templates
├── tests/                 # Test suite
│   ├── test_core.py
│   └── test_config.py
└── README.md
```

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Write clean, readable code
- Add tests for new functionality
- Update documentation as needed
- Follow existing code style

### 3. Commit with Clear Messages

```bash
git commit -m "feat: add feature description" 
git commit -m "fix: resolve bug description"
git commit -m "docs: update README"
git commit -m "test: add tests for feature"
git commit -m "refactor: improve code clarity"
```

### 4. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then open a pull request on GitHub with:
- Clear title describing the change
- Description of what changed and why
- Reference to any related issues

## Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Include tests for new functionality (aim for >80% coverage)
- Update README.md if adding user-facing features
- Ensure all tests pass before requesting review
- Respond to review feedback promptly

## Commit Message Convention

Follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation updates
- `test:` Test additions/updates
- `refactor:` Code refactoring
- `chore:` Maintenance tasks
- `perf:` Performance improvements

Example: `feat: add support for custom whisper models`

## Code Style

- **Python**: PEP 8 (enforced with Black and Flake8)
- **Naming**: descriptive variable names, avoid abbreviations
- **Functions**: should do one thing well
- **Docstrings**: include for public functions/classes
- **Type Hints**: encouraged for clarity

### Example:

```python
def extract_video_info(url: str) -> dict:
    """
    Extract video ID and metadata from TikTok URL.
    
    Args:
        url: TikTok video URL
        
    Returns:
        Dictionary with video_id and metadata
        
    Raises:
        ValueError: If URL is invalid
    """
    pass
```

## Testing Guidelines

- Write tests for all new features
- Update existing tests when modifying behavior
- Aim for >80% code coverage
- Use descriptive test names
- Mock external API calls

### Example Test:

```python
def test_normalize_peptide_names():
    """Test that common speech errors are corrected."""
    result = normalize_transcript("penny a lan")
    assert "Pinealon" in result
```

## Documentation

Update documentation when:

- Adding new features
- Changing user-facing behavior
- Adding configuration options
- Fixing documented bugs

Keep README.md updated with:
- Installation instructions
- Basic usage examples
- Configuration guide
- Troubleshooting tips

## Reporting Issues

If you find a bug:

1. Check if it's already reported
2. Create an issue with:
   - Clear, descriptive title
   - Step-by-step reproduction steps
   - Expected vs actual behavior
   - Your environment (Python version, OS, etc.)
   - Error messages/logs if applicable

## Questions?

- Check existing issues and PRs
- Review README.md and documentation
- Open a discussion for feature requests

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and improve
- Report inappropriate behavior

---

Thank you for contributing to TikTok Analyzer Pro! 🚀
