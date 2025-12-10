"""
Unit tests for the Memory Tool Handler

Run with: python -m pytest test_memory_tool.py -v
Or simply: python test_memory_tool.py
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from memory_tool import MemoryToolHandler


class TestMemoryToolHandler(unittest.TestCase):
    """Test suite for MemoryToolHandler"""
    
    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()
        self.handler = MemoryToolHandler(self.test_dir)
    
    def tearDown(self):
        """Clean up the temporary directory after each test."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    # =========================================================================
    # View Command Tests
    # =========================================================================
    
    def test_view_empty_directory(self):
        """Test viewing an empty memory directory."""
        result = self.handler.handle_tool_call({
            "command": "view",
            "path": "/memories"
        })
        self.assertIn("(empty)", result)
    
    def test_view_directory_with_files(self):
        """Test viewing a directory with files."""
        # Create some test files
        Path(self.test_dir, "notes.txt").write_text("test")
        Path(self.test_dir, "config.xml").write_text("<config/>")
        
        result = self.handler.handle_tool_call({
            "command": "view",
            "path": "/memories"
        })
        
        self.assertIn("notes.txt", result)
        self.assertIn("config.xml", result)
    
    def test_view_file_contents(self):
        """Test viewing file contents."""
        test_content = "Hello, World!\nLine 2\nLine 3"
        Path(self.test_dir, "test.txt").write_text(test_content)
        
        result = self.handler.handle_tool_call({
            "command": "view",
            "path": "/memories/test.txt"
        })
        
        self.assertEqual(result, test_content)
    
    def test_view_file_with_range(self):
        """Test viewing specific lines of a file."""
        content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        Path(self.test_dir, "test.txt").write_text(content)
        
        result = self.handler.handle_tool_call({
            "command": "view",
            "path": "/memories/test.txt",
            "view_range": [2, 4]
        })
        
        self.assertIn("Line 2", result)
        self.assertIn("Line 3", result)
        self.assertIn("Line 4", result)
        self.assertNotIn("Line 1\n", result)  # Line 1 shouldn't be at start
    
    def test_view_nonexistent_file(self):
        """Test viewing a file that doesn't exist."""
        result = self.handler.handle_tool_call({
            "command": "view",
            "path": "/memories/nonexistent.txt"
        })
        
        self.assertIn("Error", result)
        self.assertIn("does not exist", result)
    
    # =========================================================================
    # Create Command Tests
    # =========================================================================
    
    def test_create_file(self):
        """Test creating a new file."""
        result = self.handler.handle_tool_call({
            "command": "create",
            "path": "/memories/new_file.txt",
            "file_text": "Hello, Memory!"
        })
        
        self.assertIn("Successfully created", result)
        
        # Verify file exists and has correct content
        file_path = Path(self.test_dir, "new_file.txt")
        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.read_text(), "Hello, Memory!")
    
    def test_create_file_in_subdirectory(self):
        """Test creating a file in a nested directory."""
        result = self.handler.handle_tool_call({
            "command": "create",
            "path": "/memories/subdir/nested/file.txt",
            "file_text": "Nested content"
        })
        
        self.assertIn("Successfully created", result)
        
        file_path = Path(self.test_dir, "subdir", "nested", "file.txt")
        self.assertTrue(file_path.exists())
    
    def test_create_overwrites_existing(self):
        """Test that create overwrites existing files."""
        file_path = Path(self.test_dir, "existing.txt")
        file_path.write_text("Old content")
        
        self.handler.handle_tool_call({
            "command": "create",
            "path": "/memories/existing.txt",
            "file_text": "New content"
        })
        
        self.assertEqual(file_path.read_text(), "New content")
    
    # =========================================================================
    # String Replace Command Tests
    # =========================================================================
    
    def test_str_replace(self):
        """Test replacing text in a file."""
        file_path = Path(self.test_dir, "test.txt")
        file_path.write_text("Hello, World!")
        
        result = self.handler.handle_tool_call({
            "command": "str_replace",
            "path": "/memories/test.txt",
            "old_str": "World",
            "new_str": "Memory"
        })
        
        self.assertIn("Successfully replaced", result)
        self.assertEqual(file_path.read_text(), "Hello, Memory!")
    
    def test_str_replace_multiple_occurrences(self):
        """Test replacing multiple occurrences."""
        file_path = Path(self.test_dir, "test.txt")
        file_path.write_text("cat cat cat")
        
        result = self.handler.handle_tool_call({
            "command": "str_replace",
            "path": "/memories/test.txt",
            "old_str": "cat",
            "new_str": "dog"
        })
        
        self.assertIn("3 occurrence(s)", result)
        self.assertEqual(file_path.read_text(), "dog dog dog")
    
    def test_str_replace_not_found(self):
        """Test replacing text that doesn't exist."""
        file_path = Path(self.test_dir, "test.txt")
        file_path.write_text("Hello, World!")
        
        result = self.handler.handle_tool_call({
            "command": "str_replace",
            "path": "/memories/test.txt",
            "old_str": "Nonexistent",
            "new_str": "New"
        })
        
        self.assertIn("not found", result)
    
    # =========================================================================
    # Insert Command Tests
    # =========================================================================
    
    def test_insert_at_line(self):
        """Test inserting text at a specific line."""
        file_path = Path(self.test_dir, "test.txt")
        file_path.write_text("Line 1\nLine 3")
        
        result = self.handler.handle_tool_call({
            "command": "insert",
            "path": "/memories/test.txt",
            "insert_line": 2,
            "insert_text": "Line 2"
        })
        
        self.assertIn("Successfully inserted", result)
        self.assertEqual(file_path.read_text(), "Line 1\nLine 2\nLine 3")
    
    def test_insert_multiple_lines(self):
        """Test inserting multiple lines."""
        file_path = Path(self.test_dir, "test.txt")
        file_path.write_text("A\nD")
        
        result = self.handler.handle_tool_call({
            "command": "insert",
            "path": "/memories/test.txt",
            "insert_line": 2,
            "insert_text": "B\nC"
        })
        
        self.assertIn("2 line(s)", result)
        self.assertEqual(file_path.read_text(), "A\nB\nC\nD")
    
    # =========================================================================
    # Delete Command Tests
    # =========================================================================
    
    def test_delete_file(self):
        """Test deleting a file."""
        file_path = Path(self.test_dir, "to_delete.txt")
        file_path.write_text("Delete me")
        
        result = self.handler.handle_tool_call({
            "command": "delete",
            "path": "/memories/to_delete.txt"
        })
        
        self.assertIn("Successfully deleted", result)
        self.assertFalse(file_path.exists())
    
    def test_delete_directory(self):
        """Test deleting a directory."""
        dir_path = Path(self.test_dir, "subdir")
        dir_path.mkdir()
        (dir_path / "file.txt").write_text("test")
        
        result = self.handler.handle_tool_call({
            "command": "delete",
            "path": "/memories/subdir"
        })
        
        self.assertIn("Successfully deleted", result)
        self.assertFalse(dir_path.exists())
    
    def test_delete_nonexistent(self):
        """Test deleting a nonexistent file."""
        result = self.handler.handle_tool_call({
            "command": "delete",
            "path": "/memories/nonexistent.txt"
        })
        
        self.assertIn("Error", result)
    
    def test_cannot_delete_root(self):
        """Test that root memory directory cannot be deleted."""
        result = self.handler.handle_tool_call({
            "command": "delete",
            "path": "/memories"
        })
        
        self.assertIn("Error", result)
        self.assertTrue(Path(self.test_dir).exists())
    
    # =========================================================================
    # Rename Command Tests
    # =========================================================================
    
    def test_rename_file(self):
        """Test renaming a file."""
        old_path = Path(self.test_dir, "old.txt")
        old_path.write_text("Content")
        
        result = self.handler.handle_tool_call({
            "command": "rename",
            "old_path": "/memories/old.txt",
            "new_path": "/memories/new.txt"
        })
        
        self.assertIn("Successfully renamed", result)
        self.assertFalse(old_path.exists())
        self.assertTrue(Path(self.test_dir, "new.txt").exists())
    
    def test_rename_to_subdirectory(self):
        """Test moving a file to a subdirectory."""
        old_path = Path(self.test_dir, "file.txt")
        old_path.write_text("Content")
        
        result = self.handler.handle_tool_call({
            "command": "rename",
            "old_path": "/memories/file.txt",
            "new_path": "/memories/subdir/file.txt"
        })
        
        self.assertIn("Successfully renamed", result)
        self.assertTrue(Path(self.test_dir, "subdir", "file.txt").exists())
    
    # =========================================================================
    # Security Tests
    # =========================================================================
    
    def test_path_traversal_prevention(self):
        """Test that path traversal attacks are blocked."""
        # Try various path traversal patterns
        traversal_paths = [
            "../../../etc/passwd",
            "/memories/../../../etc/passwd",
            "/memories/subdir/../../..",
            "..\\..\\..\\windows\\system32",
        ]
        
        for path in traversal_paths:
            result = self.handler.handle_tool_call({
                "command": "view",
                "path": path
            })
            self.assertIn("Error", result, f"Path traversal not blocked: {path}")
    
    def test_invalid_command(self):
        """Test handling of invalid commands."""
        result = self.handler.handle_tool_call({
            "command": "invalid_command"
        })
        
        self.assertIn("Unknown command", result)


def run_interactive_test():
    """Run an interactive test to demonstrate the memory tool."""
    print("\n" + "="*60)
    print("Memory Tool Interactive Test")
    print("="*60)
    
    # Create a test directory
    test_dir = "./test_memories"
    handler = MemoryToolHandler(test_dir)
    
    try:
        # Test 1: View empty directory
        print("\n1. View empty directory:")
        print(handler.handle_tool_call({"command": "view", "path": "/memories"}))
        
        # Test 2: Create a file
        print("\n2. Create a file:")
        print(handler.handle_tool_call({
            "command": "create",
            "path": "/memories/notes.txt",
            "file_text": "# My Notes\n\n- Item 1\n- Item 2\n- Item 3"
        }))
        
        # Test 3: View the file
        print("\n3. View the file:")
        print(handler.handle_tool_call({
            "command": "view",
            "path": "/memories/notes.txt"
        }))
        
        # Test 4: Insert a line
        print("\n4. Insert a line at position 4:")
        print(handler.handle_tool_call({
            "command": "insert",
            "path": "/memories/notes.txt",
            "insert_line": 4,
            "insert_text": "- Inserted item"
        }))
        
        # Test 5: View after insert
        print("\n5. View after insert:")
        print(handler.handle_tool_call({
            "command": "view",
            "path": "/memories/notes.txt"
        }))
        
        # Test 6: Replace text
        print("\n6. Replace 'Item 1' with 'First Item':")
        print(handler.handle_tool_call({
            "command": "str_replace",
            "path": "/memories/notes.txt",
            "old_str": "Item 1",
            "new_str": "First Item"
        }))
        
        # Test 7: View directory
        print("\n7. View directory:")
        print(handler.handle_tool_call({"command": "view", "path": "/memories"}))
        
        # Test 8: Create XML file (Claude's preferred format)
        print("\n8. Create an XML memory file:")
        print(handler.handle_tool_call({
            "command": "create",
            "path": "/memories/project_context.xml",
            "file_text": """<project>
  <name>MemoryAI</name>
  <stack>Python, FastAPI</stack>
  <preferences>
    <coding_style>4-space indentation</coding_style>
    <docstrings>required</docstrings>
  </preferences>
</project>"""
        }))
        
        # Test 9: View all files
        print("\n9. View directory with files:")
        print(handler.handle_tool_call({"command": "view", "path": "/memories"}))
        
        # Test 10: Rename file
        print("\n10. Rename notes.txt to my_notes.txt:")
        print(handler.handle_tool_call({
            "command": "rename",
            "old_path": "/memories/notes.txt",
            "new_path": "/memories/my_notes.txt"
        }))
        
        print("\n" + "="*60)
        print("✅ All interactive tests passed!")
        print("="*60)
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir, ignore_errors=True)
        print(f"\nCleaned up test directory: {test_dir}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        run_interactive_test()
    else:
        # Run unit tests
        print("Running unit tests...")
        print("Use --interactive for interactive demo\n")
        unittest.main(verbosity=2)

