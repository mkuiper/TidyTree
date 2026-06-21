import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from .scanner import perform_scan
from .analyzer import analyze_tree
from .models import TidyResult

app = FastAPI(
    title="TidyTree Dashboard",
    description="Web Dashboard API for directory scanning and advisory layout analysis."
)

class ScanRequest(BaseModel):
    path: str
    max_depth: int = 5

@app.post("/api/scan", response_model=TidyResult)
def api_scan(request: ScanRequest):
    target_path = Path(request.path)
    
    # Resolve relative paths relative to workspace root if not found in current directory
    if not target_path.is_absolute() and not target_path.exists():
        workspace_root = Path(__file__).parent.parent.resolve()
        alternative_path = workspace_root / target_path
        if alternative_path.exists():
            target_path = alternative_path
            
    if not target_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Path '{request.path}' not found. Verify the folder exists. "
                   f"If scanning the test tree, run 'python generate_sample_tree.py' first."
        )
        
    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path '{target_path}' is not a directory.")
        
    try:
        # Scan and Analyze recursively
        original_tree = perform_scan(str(target_path), max_depth=request.max_depth)
        tidy_result = analyze_tree(original_tree, str(target_path))
        return tidy_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Mount the static files directory containing index.html, style.css, app.js
static_dir = Path(__file__).parent / "static"
# Ensure the static files directory exists
static_dir.mkdir(parents=True, exist_ok=True)

app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
