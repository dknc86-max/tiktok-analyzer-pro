# TikTok Analyzer Pro 🧬

An intelligent TikTok video analyzer and longevity/health protocol compiler. It fetches any creator's profile history, downloads and transcribes audio clips locally using **Faster-Whisper** (4-6x speed optimization), and automatically extracts structured protocol summaries (compounds, dosages, timing, and biological rationale) using **Gemini LLM** or a local **NLP Semantic Parser**.

---

## ⚡ Key Features

* **Sleek Glassmorphic Web App**: A premium web dashboard (Flask + Vanilla CSS + JS) with dark mode, animated ambient orbs, and clean layout controls.
* **Scroll-Free Dashboard UX**: Navigate massive profile logs instantly using **client-side category tabs** (e.g. `Protocols`, `Hormones`, `Nutrition`) and a **real-time fuzzy search box**.
* **Collapsible Protocol Cards**: Protocol cards are collapsed by default. Click any card to expand its bullet points, keeping the dashboard neat.
* **Dual-Mode Summarization**:
  * **Gemini Premium (Recommended)**: Integrates `gemini-2.5-flash` via the `google-genai` SDK with custom rate-limiting (12 RPM) to respect Gemini Free Tier limits.
  * **Structured Semantic Fallback**: If no API key is provided, an offline entity-relationship parser extracts compound details (dosages, timing keywords, and quotes) to eliminate messy text blocks.
* **Global Protocol Synthesizer**: Compiles insights across *all* transcripts into a single master summary sheet (e.g., the *4-Phase Mitochondrial Stack* or *Screen Time Stacks*).
* **Cross-Platform Compatibility**: Automatically installs and configures the correct platform-specific compiled FFmpeg binary dynamically via `imageio-ffmpeg`—no manual system installations required.

---

## 🛠️ Quick Start

### 1. Clone & Set Up Environment

Clone this repository to your local machine and navigate into the folder:

```bash
git clone https://github.com/YOUR_USERNAME/tiktok-analyzer-pro.git
cd tiktok-analyzer-pro
```

Create a Python virtual environment and activate it:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

Install all necessary dependencies:

```bash
pip install -r requirements.txt
```

### 2. Launching the Web App

Start the Flask server:

```bash
cd webapp
python app.py
```

Open your web browser and navigate to:
**`http://localhost:5001`**

*Enter any TikTok username (e.g., `@jacobnach`) and optionally paste your Google AI Studio API Key to unlock premium LLM summaries.*

### 3. Running via Command Line (CLI)

To scrape, transcribe, and summarize a profile directly from the terminal:

```bash
# Optional: Set your Gemini API Key
export GEMINI_API_KEY="your-api-key-here"

# Scrape and summarize a profile (outputs to results/<username>/)
python3 analyze_tiktok.py @jacobnach
```

To regenerate card breakdowns from existing transcripts:
```bash
python3 smart_summarizer.py
```

To compile a consolidated Master Protocols Guide across all transcripts:
```bash
python3 synthesize_protocols.py
```

---

## ⚙️ Configuration & API Setup

This tool is designed to work completely **free and offline** via local Whisper and Heuristic NLP parsers. 

However, to get premium clinical-grade summaries, we recommend getting a free **Gemini API Key**:
1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Click **Create API Key**.
3. Paste the key into the Web UI input field (which secures and caches it in your browser's `localStorage`), or set it as a shell environment variable (`export GEMINI_API_KEY="..."`).

---

## 🛡️ License

This project is licensed under the MIT License - see the LICENSE file for details.
