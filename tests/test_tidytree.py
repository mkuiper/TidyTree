import unittest
import tempfile
import json
from pathlib import Path
from tidytree.models import TreeNode, FileMetadata, Rationale
from tidytree.scanner import perform_scan, find_metadata_registries
from tidytree.analyzer import (
    analyze_tree,
    get_category,
    flatten_nested_dirs,
    resolve_stratus_exports,
    group_loose_files
)

class TestTidyTreeCore(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for scanning tests
        self.test_dir = tempfile.TemporaryDirectory()
        self.base_path = Path(self.test_dir.name)
        
    def tearDown(self):
        self.test_dir.cleanup()

    def test_category_matching(self):
        self.assertEqual(get_category(".pdf"), "Documents")
        self.assertEqual(get_category(".xlsx"), "Data & Sheets")
        self.assertEqual(get_category(".png"), "Media")
        self.assertEqual(get_category(".py"), "Source Code")
        self.assertEqual(get_category(".zip"), "Archives")
        self.assertIsNone(get_category(".unknown_extension"))

    def test_find_metadata_registries(self):
        # Create mock metadata file
        meta_dir = self.base_path / "Stratus"
        meta_dir.mkdir()
        metadata = [
            {"file_id": "file1.pdf", "title": "RealTitle.pdf", "client": "ACME"}
        ]
        with open(meta_dir / "stratus_metadata.json", "w") as f:
            json.dump(metadata, f)
            
        registry = find_metadata_registries(self.base_path)
        self.assertIn("file1.pdf", registry)
        self.assertEqual(registry["file1.pdf"]["title"], "RealTitle.pdf")

    def test_flatten_nested_dirs(self):
        # Build manual node structure: A -> B -> C -> file.txt
        file_node = TreeNode(
            name="file.txt",
            path="A/B/C/file.txt",
            original_path="A/B/C/file.txt",
            is_dir=False,
            size=10
        )
        c_node = TreeNode(
            name="C",
            path="A/B/C",
            original_path="A/B/C",
            is_dir=True,
            children=[file_node]
        )
        b_node = TreeNode(
            name="B",
            path="A/B",
            original_path="A/B",
            is_dir=True,
            children=[c_node]
        )
        a_node = TreeNode(
            name="A",
            path="A",
            original_path="A",
            is_dir=True,
            children=[b_node]
        )
        
        rationales = []
        elimination_map = {}
        optimized_node = flatten_nested_dirs(a_node, rationales, elimination_map)
        
        # A was single-child node? No, A's path is "A" != "".
        # Since A is not root (root has path == ""), and A has exactly 1 dir child, A should collapse child B.
        # B collapses C.
        # So A should directly contain file.txt!
        self.assertEqual(len(optimized_node.children), 1)
        self.assertEqual(optimized_node.children[0].name, "file.txt")
        # Check rationales
        self.assertTrue(len(rationales) >= 2) # Collapsed B and C
        self.assertIn("A/B/C", elimination_map)
        self.assertIn("A/B", elimination_map)

    def test_group_loose_files(self):
        # Create a directory node containing 5 different loose files
        files = [
            TreeNode(name="doc1.pdf", path="inbox/doc1.pdf", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".pdf")),
            TreeNode(name="doc2.docx", path="inbox/doc2.docx", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".docx")),
            TreeNode(name="sheet1.xlsx", path="inbox/sheet1.xlsx", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".xlsx")),
            TreeNode(name="sheet2.csv", path="inbox/sheet2.csv", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".csv")),
            TreeNode(name="photo.png", path="inbox/photo.png", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".png")),
        ]
        inbox_node = TreeNode(
            name="inbox",
            path="inbox",
            is_dir=True,
            children=files
        )
        
        rationales = []
        grouped_node = group_loose_files(inbox_node, rationales)
        
        # Verify that category folders were created
        child_names = [c.name for c in grouped_node.children]
        self.assertIn("Documents", child_names)
        self.assertIn("Data & Sheets", child_names)
        # photo.png is a single file in Media category, so it should stay flat
        self.assertIn("photo.png", child_names)

    def test_taxonomy_classification(self):
        # Create loose files containing government-specific glimpse texts
        files = [
            TreeNode(name="draft_bill.txt", path="inbox/draft_bill.txt", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".txt", glimpse="This draft bill outlines the council policy")),
            TreeNode(name="legal_memo.pdf", path="inbox/legal_memo.pdf", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".pdf", glimpse="Conflicting regional transport act guidelines")),
            TreeNode(name="invoice_102.xlsx", path="inbox/invoice_102.xlsx", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".xlsx", glimpse="Billing procurement details for public maintenance")),
            TreeNode(name="budget_procurement.csv", path="inbox/budget_procurement.csv", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".csv", glimpse="Tender expense audit and funding numbers")),
            TreeNode(name="annual_budget.xlsx", path="inbox/annual_budget.xlsx", is_dir=False, metadata=FileMetadata(size=10, modified_time=0.0, extension=".xlsx", glimpse="")),
        ]
        inbox_node = TreeNode(
            name="inbox",
            path="inbox",
            is_dir=True,
            children=files
        )
        rationales = []
        grouped_node = group_loose_files(inbox_node, rationales, taxonomy="government")
        child_names = [c.name for c in grouped_node.children]
        
        # Verify that government-specific taxonomy folders are created
        self.assertIn("Policy & Legislation", child_names)
        self.assertIn("Finance & Procurement", child_names)

if __name__ == "__main__":
    unittest.main()
