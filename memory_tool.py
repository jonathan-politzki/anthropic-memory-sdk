"""
Anthropic Memory Tool Handler

A client-side implementation of the Anthropic Memory Tool that enables
Claude to store and retrieve information across conversations.

This handles all memory operations: view, create, str_replace, insert, delete, rename
"""

import os
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Union


class MemoryToolHandler:
    """
    Handles memory tool operations for Claude.
    
    All operations are restricted to the /memories directory for security.
    This is a client-side implementation - Claude makes tool calls, and
    this handler executes them locally.
    """
    
    def __init__(self, base_path: str = "./memories"):
        """
        Initialize the memory tool handler.
        
        Args:
            base_path: The base directory for memory storage. All operations
                      are restricted to this directory and its subdirectories.
        """
        self.base_path = Path(base_path).resolve()
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self) -> None:
        """Create the memory directory if it doesn't exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a path and validate it's within the memory directory.
        
        Prevents directory traversal attacks by ensuring the resolved path
        is within the base memory directory.
        
        Args:
            path: The path to resolve (e.g., "/memories/notes.txt")
            
        Returns:
            The resolved Path object
            
        Raises:
            ValueError: If the path would escape the memory directory
        """
        # Strip leading /memories if present (API uses /memories prefix)
        if path.startswith("/memories"):
            path = path[9:]  # Remove "/memories"
        if path.startswith("/"):
            path = path[1:]  # Remove leading slash
        
        # Resolve the full path
        full_path = (self.base_path / path).resolve()
        
        # Security: Ensure path is within base directory
        try:
            full_path.relative_to(self.base_path)
        except ValueError:
            raise ValueError(f"Path traversal detected: {path}")
        
        return full_path
    
    def handle_tool_call(self, tool_input: Dict[str, Any]) -> str:
        """
        Handle a memory tool call from Claude.
        
        Args:
            tool_input: The input dictionary from Claude's tool call
            
        Returns:
            The result string to return to Claude
        """
        command = tool_input.get("command")
        
        handlers = {
            "view": self._handle_view,
            "create": self._handle_create,
            "str_replace": self._handle_str_replace,
            "insert": self._handle_insert,
            "delete": self._handle_delete,
            "rename": self._handle_rename,
        }
        
        handler = handlers.get(command)
        if not handler:
            return f"Error: Unknown command '{command}'"
        
        try:
            return handler(tool_input)
        except ValueError as e:
            return f"Error: {str(e)}"
        except FileNotFoundError as e:
            return f"Error: File not found - {str(e)}"
        except PermissionError as e:
            return f"Error: Permission denied - {str(e)}"
        except Exception as e:
            return f"Error: {type(e).__name__} - {str(e)}"
    
    def _handle_view(self, input_data: Dict[str, Any]) -> str:
        """
        View directory contents or file contents.
        
        Args:
            input_data: Contains 'path' and optional 'view_range' [start, end]
        """
        path = input_data.get("path", "/memories")
        view_range = input_data.get("view_range")
        
        resolved_path = self._resolve_path(path)
        
        if not resolved_path.exists():
            # If viewing the root memories directory, just show it's empty
            if resolved_path == self.base_path:
                return "Directory: /memories\n(empty)"
            return f"Error: Path does not exist: {path}"
        
        if resolved_path.is_dir():
            # List directory contents
            items = sorted(resolved_path.iterdir())
            if not items:
                return f"Directory: {path}\n(empty)"
            
            contents = [f"Directory: {path}"]
            for item in items:
                prefix = "📁 " if item.is_dir() else "📄 "
                contents.append(f"- {prefix}{item.name}")
            
            return "\n".join(contents)
        else:
            # Read file contents
            content = resolved_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            
            if view_range:
                start, end = view_range
                # Convert to 0-indexed
                start = max(0, start - 1)
                end = min(len(lines), end)
                lines = lines[start:end]
                
                # Add line numbers
                numbered_lines = []
                for i, line in enumerate(lines, start=start + 1):
                    numbered_lines.append(f"{i:4d} | {line}")
                return "\n".join(numbered_lines)
            
            return content
    
    def _handle_create(self, input_data: Dict[str, Any]) -> str:
        """
        Create or overwrite a file.
        
        Args:
            input_data: Contains 'path' and 'file_text'
        """
        path = input_data.get("path")
        file_text = input_data.get("file_text", "")
        
        if not path:
            return "Error: 'path' is required for create command"
        
        resolved_path = self._resolve_path(path)
        
        # Create parent directories if needed
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        resolved_path.write_text(file_text, encoding="utf-8")
        
        return f"Successfully created: {path}"
    
    def _handle_str_replace(self, input_data: Dict[str, Any]) -> str:
        """
        Replace text in a file.
        
        Args:
            input_data: Contains 'path', 'old_str', and 'new_str'
        """
        path = input_data.get("path")
        old_str = input_data.get("old_str")
        new_str = input_data.get("new_str")
        
        if not all([path, old_str is not None, new_str is not None]):
            return "Error: 'path', 'old_str', and 'new_str' are required"
        
        resolved_path = self._resolve_path(path)
        
        if not resolved_path.exists():
            return f"Error: File does not exist: {path}"
        
        content = resolved_path.read_text(encoding="utf-8")
        
        if old_str not in content:
            return f"Error: '{old_str}' not found in {path}"
        
        # Count occurrences
        count = content.count(old_str)
        
        # Replace all occurrences
        new_content = content.replace(old_str, new_str)
        resolved_path.write_text(new_content, encoding="utf-8")
        
        return f"Successfully replaced {count} occurrence(s) in {path}"
    
    def _handle_insert(self, input_data: Dict[str, Any]) -> str:
        """
        Insert text at a specific line.
        
        Args:
            input_data: Contains 'path', 'insert_line', and 'insert_text'
        """
        path = input_data.get("path")
        insert_line = input_data.get("insert_line")
        insert_text = input_data.get("insert_text", "")
        
        if not path or insert_line is None:
            return "Error: 'path' and 'insert_line' are required"
        
        resolved_path = self._resolve_path(path)
        
        if not resolved_path.exists():
            return f"Error: File does not exist: {path}"
        
        content = resolved_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        # Insert at the specified line (1-indexed)
        insert_idx = max(0, min(insert_line - 1, len(lines)))
        
        # Handle the insert text (may contain multiple lines)
        insert_lines = insert_text.rstrip("\n").split("\n")
        
        for i, line in enumerate(insert_lines):
            lines.insert(insert_idx + i, line)
        
        new_content = "\n".join(lines)
        resolved_path.write_text(new_content, encoding="utf-8")
        
        return f"Successfully inserted {len(insert_lines)} line(s) at line {insert_line} in {path}"
    
    def _handle_delete(self, input_data: Dict[str, Any]) -> str:
        """
        Delete a file or directory.
        
        Args:
            input_data: Contains 'path'
        """
        path = input_data.get("path")
        
        if not path:
            return "Error: 'path' is required for delete command"
        
        resolved_path = self._resolve_path(path)
        
        if not resolved_path.exists():
            return f"Error: Path does not exist: {path}"
        
        # Prevent deleting the root memories directory
        if resolved_path == self.base_path:
            return "Error: Cannot delete the root memories directory"
        
        if resolved_path.is_dir():
            shutil.rmtree(resolved_path)
            return f"Successfully deleted directory: {path}"
        else:
            resolved_path.unlink()
            return f"Successfully deleted file: {path}"
    
    def _handle_rename(self, input_data: Dict[str, Any]) -> str:
        """
        Rename or move a file/directory.
        
        Args:
            input_data: Contains 'old_path' and 'new_path'
        """
        old_path = input_data.get("old_path")
        new_path = input_data.get("new_path")
        
        if not old_path or not new_path:
            return "Error: 'old_path' and 'new_path' are required"
        
        resolved_old = self._resolve_path(old_path)
        resolved_new = self._resolve_path(new_path)
        
        if not resolved_old.exists():
            return f"Error: Source path does not exist: {old_path}"
        
        if resolved_new.exists():
            return f"Error: Destination already exists: {new_path}"
        
        # Create parent directories if needed
        resolved_new.parent.mkdir(parents=True, exist_ok=True)
        
        resolved_old.rename(resolved_new)
        
        return f"Successfully renamed {old_path} to {new_path}"
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Get the tool definition for the Anthropic API.
        
        Returns:
            The tool definition dictionary to include in API requests
        """
        return {
            "type": "memory_20250818",
            "name": "memory"
        }


def create_memory_tool_result(tool_use_id: str, content: str) -> Dict[str, Any]:
    """
    Create a tool result message for the API.
    
    Args:
        tool_use_id: The ID from the tool_use block
        content: The result content from the memory handler
        
    Returns:
        A properly formatted tool result dictionary
    """
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content
    }

