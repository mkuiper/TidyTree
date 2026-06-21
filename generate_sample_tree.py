import os
import json
import shutil
from pathlib import Path

def create_sample_tree(base_dir: Path):
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Deeply nested single-child directory (Flattening target)
    deep_path = base_dir / "projects" / "2025" / "archives" / "old_docs" / "confidential"
    deep_path.mkdir(parents=True, exist_ok=True)
    with open(deep_path / "secrets.txt", "w") as f:
        f.write("This is a secret file that is nested way too deep.")
        
    # 2. Loose disorganized files (Grouping target)
    loose_path = base_dir / "inbox"
    loose_path.mkdir(parents=True, exist_ok=True)
    
    files_to_create = {
        "annual_report.pdf": "PDF document content for annual report.",
        "budget_planning.xlsx": "Excel budget spreadsheet content.",
        "script_v1.py": "print('hello world')",
        "family_photo.png": "Binary image file simulator.",
        "tutorial.mp4": "Binary video file simulator.",
        "archive_old.zip": "Zip archive file simulator.",
        "todo_list.txt": "Simple plain text todo list: 1. Clean room 2. Buy milk",
        "styles.css": "body { background: #000; }"
    }
    
    for filename, content in files_to_create.items():
        with open(loose_path / filename, "w") as f:
            f.write(content)
            
    # 3. OneNote Export Mock (OneNote resolution target)
    onenote_path = base_dir / "OneNote Notebooks" / "Work Notebook"
    onenote_path.mkdir(parents=True, exist_ok=True)
    
    # Notebook sections
    with open(onenote_path / "Meetings.one", "w") as f:
        f.write("OneNote Section: Meetings")
    with open(onenote_path / "Projects.one", "w") as f:
        f.write("OneNote Section: Projects")
        
    # Section attachments folder
    meetings_attachments = onenote_path / "Meetings_Attachments"
    meetings_attachments.mkdir(parents=True, exist_ok=True)
    with open(meetings_attachments / " whiteboard_photo.jpg", "w") as f:
        f.write("Mock whiteboard photo attachment")
    with open(meetings_attachments / "agenda.docx", "w") as f:
        f.write("Mock meeting agenda docx")
        
    # 4. Stratus Enterprise Export Mock (Stratus metadata matching target)
    stratus_path = base_dir / "Stratus_Export"
    stratus_path.mkdir(parents=True, exist_ok=True)
    
    # Metadata file mapping UUID names to actual titles and client/matter context
    metadata = [
        {
            "file_id": "8f3d8a12-82ab-4e3d-bb62-628d0db71d33.pdf",
            "title": "Acme_Q3_Financials.pdf",
            "client": "Acme Corp",
            "matter": "Financial Audit"
        },
        {
            "file_id": "4a2e1d77-c918-4903-8dcb-1bc13e0988cc.xlsx",
            "title": "Roster_Active_Consultants.xlsx",
            "client": "Acme Corp",
            "matter": "Staffing Advisory"
        }
    ]
    
    with open(stratus_path / "stratus_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
        
    files_dir = stratus_path / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    
    with open(files_dir / "8f3d8a12-82ab-4e3d-bb62-628d0db71d33.pdf", "w") as f:
        f.write("Stratus PDF contents (UUID named)")
    with open(files_dir / "4a2e1d77-c918-4903-8dcb-1bc13e0988cc.xlsx", "w") as f:
        f.write("Stratus Excel contents (UUID named)")
    with open(files_dir / "unmapped_uuid_file.txt", "w") as f:
        f.write("Stratus export file not present in metadata")

    print(f"Sample disorganized tree generated at: {base_dir.resolve()}")

if __name__ == "__main__":
    create_sample_tree(Path("sample_disorganized_tree"))
