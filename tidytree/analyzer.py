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

TAXONOMIES = {
    "generic": {
        "description": "General purpose categorization based on file types.",
        "categories": {
            "Documents": ["pdf", "docx", "doc", "txt", "rtf", "odt", "pages", "md", "letter", "memo", "report"],
            "Data & Sheets": ["xlsx", "xls", "csv", "tsv", "json", "xml", "yaml", "yml", "database", "sql"],
            "Media": ["jpg", "jpeg", "png", "gif", "mp4", "mov", "avi", "mp3", "wav", "svg", "logo", "photo", "video"],
            "Source Code": ["py", "js", "ts", "html", "css", "c", "cpp", "java", "go", "sh", "rs", "sql", "code", "dev"],
            "Archives": ["zip", "tar", "gz", "rar", "7z", "backup", "archive"]
        }
    },
    "government": {
        "description": "Public sector and municipal architecture.",
        "categories": {
            "Policy & Legislation": ["policy", "legislation", "act", "bill", "council", "regulation", "law", "statute", "draft", "compliance", "legal", "resolution", "committee"],
            "Operations & Public Services": ["public", "service", "infrastructure", "operations", "utility", "permit", "application", "transit", "water", "waste", "road", "maintenance", "transport", "project"],
            "Finance & Procurement": ["budget", "finance", "audit", "procurement", "tender", "contract", "invoice", "billing", "grant", "funding", "expense", "purchase", "tax"],
            "Administration & HR": ["hr", "personnel", "staff", "payroll", "admin", "recruitment", "training", "benefit", "handbook", "onboarding", "leave"],
            "Communications & Relations": ["pr", "press", "media", "release", "newsletter", "public relations", "citizen", "feedback", "notice", "announcement", "publicity"]
        }
    },
    "corporate": {
        "description": "Standard business division layout.",
        "categories": {
            "Finance & Legal": ["finance", "legal", "invoice", "receipt", "tax", "audit", "contract", "agreement", "corporate", "budget", "nda", "billing", "compliance"],
            "Human Resources": ["hr", "staff", "payroll", "resume", "cv", "hiring", "review", "training", "benefits", "policy", "employee", "handbook"],
            "Marketing & Sales": ["marketing", "sales", "pr", "campaign", "ad", "social", "pitch", "lead", "proposal", "client", "customer", "leads"],
            "Product & Operations": ["product", "ops", "roadmap", "spec", "design", "feedback", "inventory", "shipping", "process", "manual", "strategy"],
            "Engineering & Tech": ["code", "dev", "api", "tech", "infrastructure", "deployment", "script", "database", "security", "bug", "software"]
        }
    },
    "academic": {
        "description": "Education and research architecture.",
        "categories": {
            "Research & Publications": ["research", "paper", "journal", "draft", "abstract", "proposal", "grant", "citation", "bibliography", "data", "experiment", "thesis", "dissertation"],
            "Teaching & Courses": ["course", "syllabus", "lecture", "slide", "homework", "exam", "quiz", "grade", "assignment", "tutorial", "reading", "lesson"],
            "Administration & Departmental": ["admin", "faculty", "minutes", "committee", "budget", "policy", "memo", "schedule", "board", "meeting"],
            "Student Portfolios & Submissions": ["student", "portfolio", "submission", "project", "presentation", "grades"]
        }
    }
}

def classify_local(name: str, glimpse: str, taxonomy_name: str) -> str:
    """
    Local keyword scoring classifier to route loose files matching a target taxonomy.
    """
    taxonomy_name = taxonomy_name.lower()
    if taxonomy_name not in TAXONOMIES:
        taxonomy_name = "generic"
        
    taxonomy = TAXONOMIES[taxonomy_name]
    scores = {}
    
    name_lower = name.lower()
    glimpse_lower = glimpse.lower()
    
    # Tokenize words to avoid partial matching of short keywords (e.g. 'c' matching 'sheet2.csv')
    import re
    name_words = set(re.findall(r'[a-zA-Z0-9]+', name_lower))
    glimpse_words = set(re.findall(r'[a-zA-Z0-9]+', glimpse_lower))
    
    for cat_name, keywords in taxonomy["categories"].items():
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if len(kw_lower) <= 2:
                # Exact word matching for short keywords
                if kw_lower in name_words:
                    score += 10
                if kw_lower in glimpse_words:
                    score += 2
            else:
                # Substring matching for longer keywords
                if kw_lower in name_lower:
                    score += 10
                if kw_lower in glimpse_lower:
                    score += 2
        scores[cat_name] = score
        
    max_cat = max(scores, key=scores.get)
    if scores[max_cat] > 0:
        return max_cat
        
    # Extension fallback mapping
    ext = Path(name).suffix.lower()
    generic_cat = None
    for gen_cat, exts in TAXONOMIES["generic"]["categories"].items():
        if ext[1:] in exts or ext in exts:
            generic_cat = gen_cat
            break
            
    if generic_cat:
        if taxonomy_name == "generic":
            return generic_cat
            
        if taxonomy_name == "government":
            mapping = {
                "Documents": "Policy & Legislation",
                "Data & Sheets": "Finance & Procurement",
                "Media": "Communications & Relations",
                "Source Code": "Operations & Public Services",
                "Archives": "Operations & Public Services"
            }
            return mapping.get(generic_cat, "Policy & Legislation")
        elif taxonomy_name == "corporate":
            mapping = {
                "Documents": "Product & Operations",
                "Data & Sheets": "Finance & Legal",
                "Media": "Marketing & Sales",
                "Source Code": "Engineering & Tech",
                "Archives": "Product & Operations"
            }
            return mapping.get(generic_cat, "Product & Operations")
        elif taxonomy_name == "academic":
            mapping = {
                "Documents": "Research & Publications",
                "Data & Sheets": "Research & Publications",
                "Media": "Teaching & Courses",
                "Source Code": "Research & Publications",
                "Archives": "Administration & Departmental"
            }
            return mapping.get(generic_cat, "Research & Publications")

    return list(taxonomy["categories"].keys())[0]

def classify_with_gemini(files_info: List[Dict[str, str]], guidance: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Call the Gemini API to get a semantically classified tree structures mapping.
    """
    import urllib.request
    import json
    
    prompt = (
        f"You are an AI directory classification assistant. Organize the listed files to match this purpose/guidance: '{guidance}'.\n"
        "Instructions:\n"
        "1. For each file, decide which logical folder it belongs to. Do not suggest deep nesting (limit directories to 2 levels maximum).\n"
        "2. Keep filenames clean but you may rename them slightly if they are chaotic (do not alter extensions).\n"
        "3. Provide your output strictly as a JSON object matching this structure:\n"
        "{\n"
        "  \"relocations\": [\n"
        "    {\n"
        "      \"original_path\": \"original path of the file\",\n"
        "      \"suggested_category\": \"folder name (e.g. Policy & Legislation)\",\n"
        "      \"suggested_name\": \"new filename (keep same as original unless chaotic)\",\n"
        "      \"reasoning\": \"brief explanation of why this file fits the category\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Files to organize:\n"
    )
    
    for idx, f in enumerate(files_info):
        prompt += f"{idx+1}. Path: '{f['path']}' | Content preview: {f['glimpse'][:200]}\n"
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    req_body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    try:
        data = json.dumps(req_body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text)
    except Exception as e:
        print("Gemini API classification failed:", e)
        return None

def classify_with_openai(files_info: List[Dict[str, str]], guidance: str, api_key: str, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Call the OpenAI API to get a semantically classified tree structures mapping.
    """
    import urllib.request
    import json
    
    prompt = (
        f"You are an AI directory classification assistant. Organize the listed files to match this purpose/guidance: '{guidance}'.\n"
        "Instructions:\n"
        "1. For each file, decide which logical folder it belongs to. Do not suggest deep nesting (limit directories to 2 levels maximum).\n"
        "2. Keep filenames clean but you may rename them slightly if they are chaotic (do not alter extensions).\n"
        "3. Provide your output strictly as a JSON object matching this structure:\n"
        "{\n"
        "  \"relocations\": [\n"
        "    {\n"
        "      \"original_path\": \"original path of the file\",\n"
        "      \"suggested_category\": \"folder name (e.g. Policy & Legislation)\",\n"
        "      \"suggested_name\": \"new filename (keep same as original unless chaotic)\",\n"
        "      \"reasoning\": \"brief explanation of why this file fits the category\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Files to organize:\n"
    )
    
    for idx, f in enumerate(files_info):
        prompt += f"{idx+1}. Path: '{f['path']}' | Content preview: {f['glimpse'][:200]}\n"
        
    url = "https://api.openai.com/v1/chat/completions"
    model_name = model if model else "gpt-4o-mini"
    
    req_body = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }
    
    try:
        data = json.dumps(req_body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        with urllib.request.urlopen(req, timeout=25) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text = res_data["choices"][0]["message"]["content"]
            return json.loads(text)
    except Exception as e:
        print("OpenAI API classification failed:", e)
        return None

def classify_with_anthropic(files_info: List[Dict[str, str]], guidance: str, api_key: str, model: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Call the Anthropic API to get a semantically classified tree structures mapping.
    """
    import urllib.request
    import json
    
    prompt = (
        f"You are an AI directory classification assistant. Organize the listed files to match this purpose/guidance: '{guidance}'.\n"
        "Instructions:\n"
        "1. For each file, decide which logical folder it belongs to. Do not suggest deep nesting (limit directories to 2 levels maximum).\n"
        "2. Keep filenames clean but you may rename them slightly if they are chaotic (do not alter extensions).\n"
        "3. Provide your output strictly as a JSON object matching this structure:\n"
        "{\n"
        "  \"relocations\": [\n"
        "    {\n"
        "      \"original_path\": \"original path of the file\",\n"
        "      \"suggested_category\": \"folder name (e.g. Policy & Legislation)\",\n"
        "      \"suggested_name\": \"new filename (keep same as original unless chaotic)\",\n"
        "      \"reasoning\": \"brief explanation of why this file fits the category\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Files to organize:\n"
    )
    
    for idx, f in enumerate(files_info):
        prompt += f"{idx+1}. Path: '{f['path']}' | Content preview: {f['glimpse'][:200]}\n"
        
    url = "https://api.anthropic.com/v1/messages"
    model_name = model if model else "claude-3-5-sonnet-latest"
    
    req_body = {
        "model": model_name,
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        data = json.dumps(req_body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        with urllib.request.urlopen(req, timeout=25) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text = res_data["content"][0]["text"]
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            return json.loads(text)
    except Exception as e:
        print("Anthropic API classification failed:", e)
        return None

def group_loose_files(node: TreeNode, rationales: List[Rationale], taxonomy: str = "generic", custom_guidance: Optional[str] = None, ai_provider: Optional[str] = None, ai_api_key: Optional[str] = None, ai_model: Optional[str] = None) -> TreeNode:
    """
    Groups loose files matching built-in or AI-guided taxonomies (supporting Gemini, OpenAI & Anthropic).
    """
    if not node.is_dir or not node.children:
        return node
        
    node.children = [group_loose_files(c, rationales, taxonomy, custom_guidance, ai_provider, ai_api_key, ai_model) for c in node.children]
    
    if node.name.endswith("_Attachments") or node.name.endswith(" Attachments"):
        return node
        
    folders = [c for c in node.children if c.is_dir]
    files = [c for c in node.children if not c.is_dir]
    
    if len(files) <= 3:
        return node
        
    # Check if AI classification is available
    if ai_api_key and ai_provider and ai_provider != "none":
        files_info = []
        for f in files:
            files_info.append({
                "path": f.path,
                "name": f.name,
                "glimpse": f.metadata.glimpse if (f.metadata and f.metadata.glimpse) else ""
            })
            
        guidance = custom_guidance or TAXONOMIES.get(taxonomy, TAXONOMIES["generic"])["description"]
        
        ai_res = None
        if ai_provider == "gemini":
            ai_res = classify_with_gemini(files_info, guidance, ai_api_key)
        elif ai_provider == "openai":
            ai_res = classify_with_openai(files_info, guidance, ai_api_key, model=ai_model)
        elif ai_provider == "anthropic":
            ai_res = classify_with_anthropic(files_info, guidance, ai_api_key, model=ai_model)
            
        if ai_res and "relocations" in ai_res:
            cat_folders = {}
            unclassified = []
            reloc_map = {r["original_path"]: r for r in ai_res["relocations"]}
            
            for f in files:
                rel = reloc_map.get(f.path)
                if rel:
                    cat = rel.get("suggested_category", "Documents").strip()
                    sug_name = rel.get("suggested_name", f.name).strip()
                    reason = rel.get("reasoning", "Classified semantically by AI.")
                    
                    if sug_name and sug_name != f.name:
                        f.name = sug_name
                        if f.metadata:
                            f.metadata.title_override = sug_name
                            
                    if cat not in cat_folders:
                        cat_folders[cat] = []
                    cat_folders[cat].append(f)
                    
                    rationales.append(Rationale(
                        action="GROUP",
                        original_path=f.original_path or f.path,
                        suggested_path="",
                        reasoning=reason
                    ))
                else:
                    unclassified.append(f)
                    
            new_children = list(folders) + unclassified
            for cat, cat_files in cat_folders.items():
                if len(cat_files) == 1:
                    new_children.append(cat_files[0])
                    rationales[:] = [r for r in rationales if r.original_path != cat_files[0].original_path]
                    continue
                    
                cat_folder = TreeNode(
                    name=cat,
                    path=f"{node.path}/{cat}" if node.path else cat,
                    original_path=node.original_path or node.path,
                    is_dir=True,
                    children=cat_files
                )
                new_children.append(cat_folder)
                
            node.children = new_children
            return node

    # Local Rule-based Taxonomy Classifier Fallback
    cat_folders = {}
    unclassified = []
    
    for f in files:
        glimpse = f.metadata.glimpse if (f.metadata and f.metadata.glimpse) else ""
        cat = classify_local(f.name, glimpse, taxonomy)
        
        if cat not in cat_folders:
            cat_folders[cat] = []
        cat_folders[cat].append(f)
        
        rationales.append(Rationale(
            action="GROUP",
            original_path=f.original_path or f.path,
            suggested_path="",
            reasoning=f"Grouped loose file '{f.name}' under category '{cat}' matching the target taxonomy."
        ))
        
    new_children = list(folders) + unclassified
    for cat, cat_files in cat_folders.items():
        if len(cat_files) == 1:
            new_children.append(cat_files[0])
            rationales[:] = [r for r in rationales if r.original_path != cat_files[0].original_path]
            continue
            
        cat_folder = TreeNode(
            name=cat,
            path=f"{node.path}/{cat}" if node.path else cat,
            original_path=node.original_path or node.path,
            is_dir=True,
            children=cat_files
        )
        new_children.append(cat_folder)
        
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

def analyze_tree(original_tree: TreeNode, target_dir: str, taxonomy: str = "generic", custom_guidance: Optional[str] = None, ai_provider: Optional[str] = None, ai_api_key: Optional[str] = None, ai_model: Optional[str] = None) -> TidyResult:
    """
    Runs the full analysis pipeline on the tree and returns the TidyResult.
    """
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
    suggested_tree = group_loose_files(suggested_tree, rationales, taxonomy, custom_guidance, ai_provider, ai_api_key, ai_model)
    
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
