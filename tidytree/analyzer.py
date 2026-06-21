import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from .models import TreeNode, Rationale, TidyResult, FileMetadata

CATEGORIES = {
    "Documents": {".pdf", ".docx", ".doc", ".txt", ".rtf", ".odt", ".pages", ".md"},
    "Data & Sheets": {".xlsx", ".xls", ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml"},
    "Media": {".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mov", ".avi", ".mp3", ".wav", ".svg"},
    "Source Code": {".py", ".js", ".ts", ".html", ".css", ".c", ".cpp", ".java", ".go", ".sh", ".rs", ".sql"},
    "Archives": {".zip", ".tar", ".gz", ".rar", ".7z"}
}

def get_category(ext: str) -> Optional[str]:
    ext = ext.lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return None

def set_original_paths(node: TreeNode, current_path: str = ""):
    """
    Ensure every node has original_path populated before we run transformations.
    """
    if not node.original_path:
        node.original_path = node.path
        
    if node.is_dir and node.children:
        for child in node.children:
            set_original_paths(child, child.path)

def flatten_nested_dirs(node: TreeNode, rationales: List[Rationale], elimination_map: Dict[str, str]) -> TreeNode:
    """
    Recursively collapses single-child folders to avoid deep nesting.
    """
    if not node.is_dir or not node.children:
        return node
        
    # Recursively optimize children
    node.children = [flatten_nested_dirs(c, rationales, elimination_map) for c in node.children]
    
    # Collapse if node is not the root, has exactly 1 child, and that child is a folder
    while node.path != "" and len(node.children) == 1 and node.children[0].is_dir:
        child = node.children[0]
        child_orig = child.original_path or child.path
        node_orig = node.original_path or node.path
        elimination_map[child_orig] = node_orig
        
        rationales.append(Rationale(
            action="FLATTEN",
            original_path=child_orig,
            suggested_path="",  # Will be adjusted in post-processing
            reasoning=f"Removed intermediate single-child folder '{child.name}' to reduce deep directory nesting."
        ))
        node.children = child.children
        
    return node

def resolve_stratus_exports(node: TreeNode, root_fs_path: Path, rationales: List[Rationale]) -> TreeNode:
    """
    Locates Stratus metadata files and organizes UUID-named files intoClient/Matter folders.
    """
    if not node.is_dir or not node.children:
        return node

    metadata_node = None
    files_dir_node = None
    
    for child in node.children:
        if child.name == "stratus_metadata.json":
            metadata_node = child
        elif child.name == "files" and child.is_dir:
            files_dir_node = child
            
    if metadata_node and files_dir_node:
        metadata_fs_path = root_fs_path / metadata_node.path
        try:
            with open(metadata_fs_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                
            meta_map = {}
            if isinstance(metadata, list):
                for entry in metadata:
                    fid = entry.get("file_id") or entry.get("filename")
                    if fid:
                        meta_map[fid] = entry
                        
            new_client_matter_nodes = {}
            unmapped_nodes = []
            
            for file_node in files_dir_node.children or []:
                meta_entry = meta_map.get(file_node.name)
                if meta_entry:
                    client = meta_entry.get("client", "Generic Client")
                    matter = meta_entry.get("matter", "Generic Matter")
                    title = meta_entry.get("title", file_node.name)
                    
                    orig_name = file_node.name
                    file_node.name = title
                    if file_node.metadata:
                        file_node.metadata.title_override = title
                        file_node.metadata.metadata_fields = {k: v for k, v in meta_entry.items() if k not in ("file_id", "filename", "title")}
                        
                    if client not in new_client_matter_nodes:
                        new_client_matter_nodes[client] = {}
                    if matter not in new_client_matter_nodes[client]:
                        new_client_matter_nodes[client][matter] = []
                        
                    new_client_matter_nodes[client][matter].append(file_node)
                    
                    rationales.append(Rationale(
                        action="RENAME_AND_MOVE",
                        original_path=file_node.original_path or file_node.path,
                        suggested_path="",  # Post-processed
                        reasoning=f"Renamed UUID-coded file '{orig_name}' to human-friendly '{title}' and organized under client '{client}' / matter '{matter}' using metadata."
                    ))
                else:
                    unmapped_nodes.append(file_node)
                    rationales.append(Rationale(
                        action="MOVE",
                        original_path=file_node.original_path or file_node.path,
                        suggested_path="",  # Post-processed
                        reasoning=f"Moved unmapped export file '{file_node.name}' to the 'Unmapped' directory."
                    ))
                    
            # Update children: remove the 'files' folder, keep metadata and add restructured directories
            node.children = [c for c in node.children if c != files_dir_node]
            
            for client, matters in new_client_matter_nodes.items():
                client_folder = TreeNode(
                    name=client,
                    path=f"{node.path}/{client}" if node.path else client,
                    original_path=node.original_path,
                    is_dir=True,
                    children=[]
                )
                for matter, nodes in matters.items():
                    matter_folder = TreeNode(
                        name=matter,
                        path=f"{client_folder.path}/{matter}",
                        original_path=node.original_path,
                        is_dir=True,
                        children=nodes
                    )
                    client_folder.children.append(matter_folder)
                node.children.append(client_folder)
                
            if unmapped_nodes:
                unmapped_folder = TreeNode(
                    name="Unmapped",
                    path=f"{node.path}/Unmapped" if node.path else "Unmapped",
                    original_path=node.original_path,
                    is_dir=True,
                    children=unmapped_nodes
                )
                node.children.append(unmapped_folder)
                
        except Exception:
            # Revert to scanning children normally if exception occurs
            pass
            
    # Process remaining directories
    node.children = [resolve_stratus_exports(c, root_fs_path, rationales) for c in node.children or []]
    return node

def group_loose_files(node: TreeNode, rationales: List[Rationale]) -> TreeNode:
    """
    Groups loose files into standard folders based on extensions if folder is disorganized.
    """
    if not node.is_dir or not node.children:
        return node
        
    node.children = [group_loose_files(c, rationales) for c in node.children]
    
    # Don't group OneNote attachments folders (they are deliberately grouped with notes)
    if node.name.endswith("_Attachments") or node.name.endswith(" Attachments"):
        return node
        
    folders = [c for c in node.children if c.is_dir]
    files = [c for c in node.children if not c.is_dir]
    
    if len(files) <= 3:
        return node
        
    categorized_files = {}
    unclassified_files = []
    
    for f in files:
        ext = f.metadata.extension if f.metadata else ""
        cat = get_category(ext)
        if cat:
            if cat not in categorized_files:
                categorized_files[cat] = []
            categorized_files[cat].append(f)
        else:
            unclassified_files.append(f)
            
    # Only perform grouping if they belong to at least 2 categories or one category has >3 files
    if len(categorized_files) < 2 and not any(len(lst) > 3 for lst in categorized_files.values()):
        return node
        
    new_children = list(folders) + unclassified_files
    
    for cat, cat_files in categorized_files.items():
        if len(cat_files) == 1:
            new_children.append(cat_files[0])
            continue
            
        cat_folder = TreeNode(
            name=cat,
            path=f"{node.path}/{cat}" if node.path else cat,
            original_path=node.original_path or node.path,
            is_dir=True,
            children=cat_files
        )
        new_children.append(cat_folder)
        
        for f in cat_files:
            rationales.append(Rationale(
                action="GROUP",
                original_path=f.original_path or f.path,
                suggested_path="",  # Post-processed
                reasoning=f"Grouped loose file '{f.name}' under category directory '{cat}' to tidy up parent folder."
            ))
            
    node.children = new_children
    return node

def recalculate_paths(node: TreeNode, parent_path: str = ""):
    """
    Recalculate path fields for all nodes based on parent hierarchy.
    """
    if parent_path:
        node.path = f"{parent_path}/{node.name}"
    else:
        node.path = "" if node.path == "" else node.name
        
    if node.is_dir and node.children:
        for child in node.children:
            recalculate_paths(child, node.path)

def build_original_to_final_map(node: TreeNode, path_map: Dict[str, str]):
    """
    Maps original path to current recalculated path.
    """
    if node.original_path:
        path_map[node.original_path] = node.path
    if node.is_dir and node.children:
        for child in node.children:
            build_original_to_final_map(child, path_map)

def analyze_tree(original_tree: TreeNode, target_dir: str) -> TidyResult:
    """
    Runs the full analysis pipeline on the tree and returns the TidyResult.
    """
    # Create deep copy for suggestions
    suggested_tree = original_tree.model_copy(deep=True)
    
    # 1. Initialize original paths
    set_original_paths(suggested_tree)
    
    rationales: List[Rationale] = []
    root_fs_path = Path(target_dir).resolve()
    
    # 2. Run Nesting Flattening Pass
    elimination_map: Dict[str, str] = {}
    suggested_tree = flatten_nested_dirs(suggested_tree, rationales, elimination_map)
    
    # 3. Run Stratus Resolution Pass
    suggested_tree = resolve_stratus_exports(suggested_tree, root_fs_path, rationales)
    
    # 4. Run Loose Files Grouping Pass
    suggested_tree = group_loose_files(suggested_tree, rationales)
    
    # 5. Recalculate paths on the new structure
    recalculate_paths(suggested_tree, parent_path="")
    
    # 6. Post-process rationales to match actual final suggested paths
    path_map: Dict[str, str] = {}
    build_original_to_final_map(suggested_tree, path_map)
    
    aligned_rationales: List[Rationale] = []
    seen_relocations = set()
    has_existing_rationale = set()
    
    for r in rationales:
        final_suggested = r.original_path
        if final_suggested in elimination_map:
            current = final_suggested
            while current in elimination_map:
                current = elimination_map[current]
            final_suggested = path_map.get(current, current)
        else:
            final_suggested = path_map.get(final_suggested, final_suggested)
            
        if final_suggested == r.original_path:
            continue
        key = (r.original_path, final_suggested)
        if key in seen_relocations:
            continue
        seen_relocations.add(key)
        
        aligned_rationales.append(Rationale(
            action=r.action,
            original_path=r.original_path,
            suggested_path=final_suggested,
            reasoning=r.reasoning
        ))
        has_existing_rationale.add(r.original_path)
        
    # Walk tree to add silent relocations for files due to flattening
    def find_silent_relocations(node: TreeNode):
        if not node.is_dir:
            if node.original_path and node.original_path != node.path:
                if node.original_path not in has_existing_rationale:
                    aligned_rationales.append(Rationale(
                        action="FLATTEN",
                        original_path=node.original_path,
                        suggested_path=node.path,
                        reasoning=f"Relocated file '{node.name}' to a shallower folder to bypass flattened intermediate directories."
                    ))
        elif node.children:
            for c in node.children:
                find_silent_relocations(c)
                
    find_silent_relocations(suggested_tree)
        
    # Sort children in the final suggested tree for consistency
    def sort_tree_children(node: TreeNode):
        if node.is_dir and node.children:
            node.children.sort(key=lambda x: (not x.is_dir, x.name.lower()))
            for c in node.children:
                sort_tree_children(c)
                
    sort_tree_children(suggested_tree)
    
    return TidyResult(
        original_tree=original_tree,
        suggested_tree=suggested_tree,
        rationales=aligned_rationales
    )
