# Feature Plan: All 6 Enhancements

## Guiding Principle
Every feature must work in both the Flask webapp (`webapp/`) and the CLI (`analyze_tiktok.py`), drawing from a single `core.py` to avoid duplication. All ingest and state lives at the repo root next to `transcripts.md`.

---

## 1. Persistent Job State (SQLite)

**What:** Replace the in-memory `jobs = {}` with a tiny SQLite database so analyses survive server restarts.

**Changes:**
- `webapp/analyzer.py`: Initialize `sqlite3.connect('job_state.db')` at module load. Replace dict CRUD with `INSERT/UPDATE/SELECT` on a `jobs` table (`job_id TEXT PK, status, progress, total, current_video, message, results_json, created_at`).
- `webapp/app.py`: No changes — `get_job_status` signature stays the same.
- CLI (`analyze_tiktok.py`): No changes needed (runs synchronously, no job state).

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  status TEXT DEFAULT 'starting',
  progress INTEGER DEFAULT 0,
  total INTEGER DEFAULT 0,
  current_video TEXT DEFAULT '',
  message TEXT DEFAULT '',
  results_json TEXT DEFAULT '[]',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. Resume Failed Analyses (Checkpointing)

**What:** If a job errors or the server restarts, let users pick up where they left off instead of re-transcribing already-done videos.

**Changes:**
- `webapp/analyzer.py` (`analyze_profile_background`):
  - After each successful video, update `jobs[job_id]["progress"]` (already done).
  - On startup of a new job, after fetching entries, check SQLite: if a matching `job_id` exists with `status='error'` or `status='transcribing'`, prompt the user to resume via a new API endpoint.
- `webapp/app.py`: Add `/api/resume/<job_id>` that kicks off `analyze_profile_background` with the existing job_id. The function reads `jobs[job_id]["progress"]` from SQLite to know where to start.
- `core.py` / `analyzer.py`: The transcribe loop already uses `enumerate(entries)`; just start the loop from `idx = existing_progress` instead of 0 when resuming.

**UX:** If a failed job exists, the status page shows a "Resume" button.

---

## 3. Creator Comparison View

**What:** Let users run a second analysis and overlay its results against the first, surfacing consensus and divergent recommendations.

**Changes:**
- `webapp/templates/index.html`: Add a second input field `#targetInput2` with a "Compare" toggle. When toggled on, the form sends two targets.
- `webapp/app.py`: `/api/analyze` accepts optional `target2`. Starts a second job. Results page stores both `primaryResults` and `comparisonResults`.
- `webapp/static/app.js`: New tab in the infographics view: `comparisonBtn`. Renders a side-by-side compound frequency chart (two ApexCharts series overlaid) and a "Shared vs Unique" panel listing compounds both creators mention vs. only one does.
- Mind map: overlay both creator topic networks as separate root nodes connected by a dashed "comparison" edge, colored distinctly.

**Backend:** Both analyses write to the same `transcripts.md` (cache dedup by video URL), so comparison is just a second pass through the same cache.

---

## 4. Dosage Extraction Dashboard

**What:** Parse `{compound → [{dose, unit, route, source_video}]}` from transcripts with regex and surface it as a dedicated dashboard panel.

**Changes:**
- `core.py`: Add `extract_dosages(transcript, source_title, source_url)` → returns `List[Dict]` with keys `compound, dose, unit, route, source_title, source_url`. Regex patterns added to the existing `extract_fallback_bullets` logic but extracted into a shared helper.
- `webapp/analyzer.py`: In the per-video loop, call `extract_dosages` and accumulate into `job[job_id]["dosages"]` (also persisted to SQLite).
- `webapp/static/app.js`: New `dosageChart` (ApexCharts grouped bar or table) in the infographics view. Table columns: Compound | Dose | Unit | Route | Source Video (linked).
- `synthesize_protocols.py`: Use the structured dosage data in `synthesize_offline` instead of regex-scraping ad-hoc.

**Regex strategy:** `(\d+(?:\.\d+)?)\s*(mg|mcg|milligrams?|micrograms?|iu|units?)\s*(?:per\s+)?(day|week|month)?\s*(?:via|through|as)?\s*(subq|oral|nasal|topical)?`

---

## 5. Transcript Cache Compaction

**What:** Prevent `transcripts.md` from growing without bound by deduplicating on video ID and pruning old entries.

**Changes:**
- `core.py`: Add `compact_transcripts_cache(filepath, max_age_days=90)`:
  1. Parse all blocks.
  2. Build `{video_id: (title, url, transcript, timestamp)}`.
  3. Drop entries where `video_id` is None (unparseable) or `timestamp > max_age_days`.
  4. Deduplicate: keep the first occurrence per `video_id`.
  5. Rewrite the file.
- `webapp/analyzer.py`: Call `compact_transcripts_cache` in a background thread when `transcripts.md` exceeds 10 MB or daily at first load.
- `analyze_tiktok.py`: Add `--compact` flag. Also auto-run if file > 10 MB.
- Add a `last_compacted` timestamp at the top of `transcripts.md` to avoid re-compacting on every run.

---

## 6. Export to Notion / Obsidian

**What:** One-click export of results to Notion (via API) and Obsidian (via `.md` file with vault-compatible frontmatter).

**Changes:**
- `webapp/templates/index.html`: Add two new buttons: "Export to Notion" and "Export for Obsidian".
- `webapp/app.py`: New `/api/export/notion` and `/api/export/obsidian` endpoints.
  - Obsidian: Generate a `.md` with YAML frontmatter (`--- tags, creator, category, compounds ---`) and `[[]]` wiki-links for compounds. Write to `/results/<creator>/`.
  - Notion: POST each result card as a Notion page block via `requests.post('https://api.notion.com/v1/pages', ...)`. Requires `NOTION_API_KEY` and `NOTION_PARENT_PAGE_ID` env vars.
- `webapp/static/app.js`: Buttons call the endpoints and trigger a file download (Obsidian) or open Notion URL (Notion).
- Fallback: If no API keys are configured, the buttons show a tooltip directing the user to settings.

---

## Implementation Order

| Priority | Feature | Rationale |
|----------|---------|-----------|
| 1 | Dosage Extraction | Highest user value; feeds into comparison and synthesis |
| 2 | Persistent Job State | Unblocks long-running analyses; low risk |
| 3 | Resume Failed Analyses | Natural follow-on to #2 |
| 4 | Cache Compaction | Prevents bloat; self-contained |
| 5 | Creator Comparison | Builds on dosage data + stable job state |
| 6 | Notion/Obsidian Export | Polish feature; depends on structured data from #1 |
