import os
import json
import mimetypes
from pathlib import Path
from typing import Dict, Any, List
from .models import FileMetadata, TreeNode

def find_metadata_registries(root_path: Path) -> Dict[str, Dict[str, Any]]:
    """
    Search recursively for metadata files (like stratus_metadata.json) and compile 
    a file name mapping registry to override generated UUID names.
    """
    registry = {}
    # Find any *metadata*.json file
    for path in root_path.rglob("*metadata*.json"):
        if path.is_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for entry in data:
                            file_id = entry.get("file_id") or entry.get("filename")
                            if file_id:
                                registry[file_id] = entry
                    elif isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, dict):
                                registry[k] = v
                            else:
                                registry[k] = {"title": v}
            except Exception:
                # Silently ignore malformed files during scanner phase
                pass
    return registry

def scan_path(root_path: Path, current_path: Path, metadata_registry: Dict[str, Dict[str, Any]], max_depth: int, current_depth: int = 0) -> TreeNode:
    """
    Recursively scan a directory or file and return its TreeNode representation.
    """
    is_dir = current_path.is_dir()
    
    # Calculate relative path
    try:
        rel_path = str(current_path.relative_to(root_path))
        if rel_path == ".":
            rel_path = ""
    except ValueError:
        # If not relative (e.g. symlinks), use absolute
        rel_path = str(current_path.resolve())

    name = current_path.name
    if not name and rel_path == "":
        name = root_path.name or str(root_path)

    if not is_dir:
        stat = current_path.stat()
        ext = current_path.suffix.lower()
        mime, _ = mimetypes.guess_type(current_path)
        
        # Look up in the metadata registry (matching exact filename)
        title_override = None
        meta_fields = None
        if current_path.name in metadata_registry:
            entry = metadata_registry[current_path.name]
            title_override = entry.get("title")
            meta_fields = {k: v for k, v in entry.items() if k not in ("file_id", "filename", "title")}
            
        metadata = FileMetadata(
            size=stat.st_size,
            modified_time=stat.st_mtime,
            extension=ext,
            mime_type=mime,
            title_override=title_override,
            metadata_fields=meta_fields
        )
        return TreeNode(
            name=name,
            path=rel_path,
            is_dir=False,
            size=stat.st_size,
            metadata=metadata
        )

    # Walk directory
    children = []
    total_size = 0
    
    if current_depth < max_depth:
        try:
            for entry in os.scandir(current_path):
                # Skip hidden files and folders
                if entry.name.startswith(".") and entry.name != ".":
                    continue
                child_node = scan_path(
                    root_path=root_path,
                    current_path=Path(entry.path),
                    metadata_registry=metadata_registry,
                    max_depth=max_depth,
                    current_depth=current_depth + 1
                )
                children.append(child_node)
                total_size += child_node.size
        except PermissionError:
            # Silently skip folders with insufficient permissions
            pass

    # Sort children: directories first, then files, both alphabetically
    children.sort(key=lambda x: (not x.is_dir, x.name.lower()))

    return TreeNode(
        name=name,
        path=rel_path,
        is_dir=True,
        size=total_size,
        children=children
    )

def perform_scan(target_dir: str, max_depth: int = 5) -> TreeNode:
    """
    Scans a directory and returns its full TreeNode representation.
    """
    path = Path(target_dir).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Target path does not exist: {target_dir}")
        
    registry = find_metadata_registries(path)
    return scan_path(path, path, registry, max_depth)
