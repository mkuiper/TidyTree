from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class FileMetadata(BaseModel):
    size: int
    modified_time: float
    extension: str
    mime_type: Optional[str] = None
    title_override: Optional[str] = None
    glimpse: Optional[str] = None
    metadata_fields: Optional[Dict[str, Any]] = None

class TreeNode(BaseModel):
    name: str
    path: str  # Relative path from scan root
    original_path: Optional[str] = None  # Track where this file/folder came from
    is_dir: bool
    size: int = 0
    children: Optional[List["TreeNode"]] = None
    metadata: Optional[FileMetadata] = None

class Rationale(BaseModel):
    action: str  # "MOVE", "FLATTEN", "GROUP", "RENAME", "KEEP"
    original_path: str
    suggested_path: str
    reasoning: str

class TidyResult(BaseModel):
    original_tree: TreeNode
    suggested_tree: TreeNode
    rationales: List[Rationale]
