import os
from pathlib import Path

def load_dotenv(target_dir: str = None) -> None:
    """
    Search for a .env file and load variables into os.environ.
    Checks:
    1. The target directory being scanned (if provided)
    2. The current working directory (Path.cwd())
    3. The TidyTree workspace root directory (Path(__file__).parent.parent)
    """
    paths_to_check = []
    
    if target_dir:
        paths_to_check.append(Path(target_dir))
        
    paths_to_check.append(Path.cwd())
    
    # Workspace root: directory containing the tidytree package
    workspace_root = Path(__file__).parent.parent.resolve()
    paths_to_check.append(workspace_root)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for p in paths_to_check:
        resolved = p.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_paths.append(resolved)
            
    for dir_path in unique_paths:
        dotenv_path = dir_path / ".env"
        if dotenv_path.exists() and dotenv_path.is_file():
            try:
                with open(dotenv_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip()
                            # Strip outer quotes if any
                            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                                val = val[1:-1]
                            # Set the variable if key is valid
                            if key:
                                os.environ[key] = val
            except Exception:
                # Silently ignore read errors
                pass
