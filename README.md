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

#### Markdown Format Output
```bash
.venv/bin/python main.py scan -p sample_disorganized_tree -d 8 -f markdown
```

#### JSON Format Output
```bash
.venv/bin/python main.py scan -p sample_disorganized_tree -d 8 -f json
```

---

### 2. Web Dashboard

Launch the FastAPI web server to explore structures interactively:
```bash
.venv/bin/python main.py dashboard --port 8000
```
Then navigate to **http://127.0.0.1:8000** in your browser.

#### Interactive Features:
- **Collapsible Roots**: Click any folder node to expand or collapse it.
- **Before & After Sync**: Highlighted nodes show modified files/directories.
- **Cross-Highlighting**: Click any row in the **Suggested Optimizations** table at the bottom to highlight the affected files in both the "Before" (red outline) and "After" (green outline) trees, automatically scrolling them into view.
