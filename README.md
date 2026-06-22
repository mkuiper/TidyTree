# TidyTree 🌲

**TidyTree** is an intelligent directory organization assistant. It safely crawls a messy directory structure, parses files (including complex exports from Stratus or OneNote), and devises a simplified, logically superior organizational structure.

> [!IMPORTANT]
> **Safety First (Read-Only Advice):** TidyTree is strictly advisory. It crawls and analyzes directories in a read-only fashion. It **never** moves, alters, renames, or deletes your actual files on disk.

---

## Key Features

1. **Safety Guarantee**: 100% read-only engine. No data loss risk.
2. **Deep-Nesting Flattening**: Collapses single-child subdirectory chains to flatten path access.
3. **Smart Categorization**: Groups messy loose files into standard folders (`Documents`, `Source Code`, `Data & Sheets`, `Media`, `Archives`) based on extensions.
4. **OneNote Attacher Resolver**: Preserves notes section attachments grouped together alongside section `.one` files.
5. **Stratus Enterprise Resolution**: Parses enterprise metadata JSON dumps to restore UUID filenames to human titles, and automatically builds structured client/matter directory hierarchies.
6. **Double Presentation Interfaces**:
   - **CLI Tool**: Headless execution with text (ASCII tree), JSON, and Markdown reporting options.
   - **Web Dashboard**: Interactive side-by-side "Before vs. After" comparison with collapsible nodes and cross-highlighting.

---

## Technical Stack & Architecture

- **Backend**: Python 3.11+, FastAPI (Web Dashboard API), Click (CLI interface), Pydantic (Strong types).
- **Environment & Dependency Manager**: `uv` (exclusively).
- **Frontend Dashboard**: HTML5, Vanilla CSS (Glassmorphism & animations), Vanilla JS (Interactive trees, path traversal, highlighting, scrolling).

---

## Installation & Setup

Ensure you have [uv](https://github.com/astral-sh/uv) installed.

### 1. Synchronize Virtual Environment
Initialize the environment and download dependencies:
```bash
uv sync
```

### 2. Generate a Test Fixture
We include a generator script to build a complex, messy sample directory including deep nesting, loose files, OneNote backups, and a Stratus export mapping UUIDs:
```bash
.venv/bin/python generate_sample_tree.py
```
This creates a directory named `sample_disorganized_tree/` in the workspace root.

---

## Usage Guide

### 1. Command Line Interface (CLI)

Run scans and get structure reports directly in your terminal.

#### Simple Scan (Text Output)
```bash
.venv/bin/python main.py scan -p sample_disorganized_tree -d 8
```

#### Scan with Specific Taxonomy Template (e.g. Government Agency)
```bash
.venv/bin/python main.py scan -p sample_disorganized_tree -t government
```

#### Markdown Format Output
```bash
.venv/bin/python main.py scan -p sample_disorganized_tree -d 8 -f markdown
```

#### JSON Format Output
```bash
.venv/bin/python main.py scan -p sample_disorganized_tree -d 8 -f json
```

#### AI Reorganization with Custom Guidance
If you have an API key set, you can run semantic, context-aware reorganization using Google Gemini, OpenAI GPT, or Anthropic Claude:
```bash
.venv/bin/python main.py scan -p sample_disorganized_tree -g "We are a municipal team managing permits and act revisions." --provider anthropic
```

---

### 2. API Key Configuration (`.env`)

You can supply API keys for Google Gemini, OpenAI GPT, or Anthropic Claude models using a `.env` file. TidyTree automatically searches for a `.env` file in:
1. The target directory being scanned.
2. The current working directory (CWD).
3. The root of the TidyTree workspace.

Example `.env` content:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

---

### 3. Web Dashboard

Launch the FastAPI web server to explore structures interactively:
```bash
.venv/bin/python main.py dashboard --port 8000
```
Then navigate to **http://127.0.0.1:8000** in your browser.

#### Dashboard Features:
- **Collapsible Roots**: Click any folder node to expand or collapse it.
- **Before & After Sync**: Highlighted nodes show modified files/directories.
- **Cross-Highlighting**: Click any row in the **Suggested Optimizations** table at the bottom to highlight the affected files in both the "Before" (red outline) and "After" (green outline) trees, automatically scrolling them into view.
- **Help Guide Modal**: Click the **❓ Help Guide** chip at the top right to see full details on taxonomy templates (Generic, Government, Corporate, Academic) and interface features.
- **Real-Time Directory Search**: Search filenames directly in the search bar. Non-matching files fade out, matches are highlighted in yellow, and matching folder paths automatically expand.
- **Symbolic Views & Metrics**:
  - Compare file counts, folder counts, and maximum nesting depths side-by-side.
  - A visual category distribution bar displays the proportional allocation of suggested folders.
