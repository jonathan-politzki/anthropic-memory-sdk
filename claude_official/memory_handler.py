"""
Claude Official Memory Implementation

This is an exact implementation following Anthropic's official documentation.
Reference: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool

Features:
- All operations restricted to /memories directory
- Path traversal protection
- Supports all 6 official commands: view, create, str_replace, insert, delete, rename
"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys
sys.path.append('..')
from memory_interface import MemoryInterface
# Removed latency tracking for clean testing


class ClaudeOfficialMemory(MemoryInterface):
    """
    Official Claude memory implementation as per Anthropic documentation.
    
    This follows the exact specification from:
    - https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
    - https://github.com/anthropics/anthropic-sdk-python/blob/main/examples/memory/basic.py
    """
    
    def __init__(self, base_path: str = "./memories"):
        """Initialize with base memory directory"""
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Removed latency tracking for clean testing
        
        # Track operation counts for metrics
        self.operation_counts = {
            'view': 0,
            'create': 0,
            'str_replace': 0,
            'insert': 0,
            'delete': 0,
            'rename': 0
        }
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Return the official tool definition for Claude.
        
        As per docs, this is the minimal definition needed.
        """
        return {
            "type": "memory_20250818",
            "name": "memory"
        }
    
    def _validate_path(self, path: str) -> Path:
        """
        Validate and resolve path with security checks.
        
        Prevents directory traversal attacks.
        """
        # Remove /memories prefix if present
        if path.startswith("/memories"):
            path = path[9:]
        if path.startswith("/"):
            path = path[1:]
        
        # Resolve full path
        full_path = (self.base_path / path).resolve()
        
        # Security check - ensure path is within base directory
        try:
            full_path.relative_to(self.base_path)
        except ValueError:
            raise ValueError(f"Path traversal detected: {path}")
        
        return full_path
    
    def handle_tool_call(self, tool_input: Dict[str, Any]) -> str:
        """
        Main handler for all memory tool calls.
        
        Dispatches to appropriate command handler.
        """
        command = tool_input.get("command")
        
        if not command:
            return "Error: No command specified"
        
        # Map commands to handlers
        handlers = {
            "view": self._handle_view,
            "create": self._handle_create,
            "str_replace": self._handle_str_replace,
            "insert": self._handle_insert,
            "delete": self._handle_delete,
            "rename": self._handle_rename
        }
        
        handler = handlers.get(command)
        if not handler:
            return f"Error: Unknown command '{command}'"
        
        try:
            self.operation_counts[command] += 1
            return handler(tool_input)
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _handle_view(self, input_data: Dict[str, Any]) -> str:
        """Handle view command - show directory or file contents"""
        path = input_data.get("path", "/memories")
        view_range = input_data.get("view_range")
        
        return self.view(path, view_range)
    
    def view(self, path: str, view_range: Optional[List[int]] = None) -> str:
        """View directory or file contents"""
        resolved_path = self._validate_path(path)
        
        # Handle root memories directory
        if not resolved_path.exists():
            if resolved_path == self.base_path:
                return "Directory: /memories\n(empty)"
            return f"Error: Path does not exist: {path}"
        
        # Directory listing
        if resolved_path.is_dir():
            items = sorted(resolved_path.iterdir())
            if not items:
                return f"Directory: {path}\n(empty)"
            
            lines = [f"Directory: {path}"]
            for item in items:
                if item.is_dir():
                    lines.append(f"- 📁 {item.name}")
                else:
                    size = item.stat().st_size
                    lines.append(f"- 📄 {item.name} ({size} bytes)")
            
            return "\n".join(lines)
        
        # File contents
        else:
            content = resolved_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            
            if view_range:
                start, end = view_range
                # Convert to 0-indexed
                start = max(0, start - 1)
                end = min(len(lines), end)
                lines = lines[start:end]
                return "\n".join(lines)
            
            return content
    
    def _handle_create(self, input_data: Dict[str, Any]) -> str:
        """Handle create command"""
        path = input_data.get("path")
        file_text = input_data.get("file_text", "")
        
        if not path:
            return "Error: No path specified"
        
        return self.create(path, file_text)
    
    def create(self, path: str, file_text: str) -> str:
        """Create or overwrite a file"""
        resolved_path = self._validate_path(path)
        
        # Create parent directories if needed
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        resolved_path.write_text(file_text, encoding="utf-8")
        
        return f"Created file: {path}"
    
    def _handle_str_replace(self, input_data: Dict[str, Any]) -> str:
        """Handle str_replace command"""
        path = input_data.get("path")
        old_str = input_data.get("old_str")
        new_str = input_data.get("new_str")
        
        if not all([path, old_str is not None, new_str is not None]):
            return "Error: Missing required parameters for str_replace"
        
        return self.str_replace(path, old_str, new_str)
    
    def str_replace(self, path: str, old_str: str, new_str: str) -> str:
        """Replace text in a file"""
        resolved_path = self._validate_path(path)
        
        if not resolved_path.exists():
            return f"Error: File does not exist: {path}"
        
        if resolved_path.is_dir():
            return f"Error: Cannot replace text in directory: {path}"
        
        content = resolved_path.read_text(encoding="utf-8")
        
        if old_str not in content:
            return f"Error: String not found in file: {old_str[:50]}..."
        
        # Count occurrences
        count = content.count(old_str)
        
        # Replace all occurrences
        new_content = content.replace(old_str, new_str)
        resolved_path.write_text(new_content, encoding="utf-8")
        
        return f"Replaced {count} occurrence(s) in {path}"
    
    def _handle_insert(self, input_data: Dict[str, Any]) -> str:
        """Handle insert command"""
        path = input_data.get("path")
        insert_line = input_data.get("insert_line")
        insert_text = input_data.get("insert_text", "")
        
        if not path or insert_line is None:
            return "Error: Missing required parameters for insert"
        
        return self.insert(path, insert_line, insert_text)
    
    def insert(self, path: str, insert_line: int, insert_text: str) -> str:
        """Insert text at a specific line"""
        resolved_path = self._validate_path(path)
        
        if not resolved_path.exists():
            # Create new file if it doesn't exist
            if insert_line == 0:
                resolved_path.write_text(insert_text, encoding="utf-8")
                return f"Created new file with content at {path}"
            else:
                return f"Error: Cannot insert at line {insert_line} in non-existent file"
        
        if resolved_path.is_dir():
            return f"Error: Cannot insert text into directory: {path}"
        
        content = resolved_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        # Handle line number bounds
        if insert_line < 0:
            return "Error: Line number must be non-negative"
        
        if insert_line > len(lines):
            # Pad with empty lines if needed
            while len(lines) < insert_line:
                lines.append("")
        
        # Insert the text
        lines.insert(insert_line, insert_text)
        
        # Write back
        resolved_path.write_text("\n".join(lines), encoding="utf-8")
        
        return f"Inserted text at line {insert_line} in {path}"
    
    def _handle_delete(self, input_data: Dict[str, Any]) -> str:
        """Handle delete command"""
        path = input_data.get("path")
        
        if not path:
            return "Error: No path specified"
        
        return self.delete(path)
    
    def delete(self, path: str) -> str:
        """Delete a file or directory"""
        resolved_path = self._validate_path(path)
        
        if not resolved_path.exists():
            return f"Error: Path does not exist: {path}"
        
        if resolved_path.is_dir():
            # Remove directory and all contents
            shutil.rmtree(resolved_path)
            return f"Deleted directory: {path}"
        else:
            # Remove file
            resolved_path.unlink()
            return f"Deleted file: {path}"
    
    def _handle_rename(self, input_data: Dict[str, Any]) -> str:
        """Handle rename command"""
        old_path = input_data.get("old_path")
        new_path = input_data.get("new_path")
        
        if not old_path or not new_path:
            return "Error: Both old_path and new_path required"
        
        return self.rename(old_path, new_path)
    
    def rename(self, old_path: str, new_path: str) -> str:
        """Rename or move a file/directory"""
        old_resolved = self._validate_path(old_path)
        new_resolved = self._validate_path(new_path)
        
        if not old_resolved.exists():
            return f"Error: Source path does not exist: {old_path}"
        
        if new_resolved.exists():
            return f"Error: Destination already exists: {new_path}"
        
        # Create parent directories for destination if needed
        new_resolved.parent.mkdir(parents=True, exist_ok=True)
        
        # Move/rename
        old_resolved.rename(new_resolved)
        
        return f"Renamed {old_path} to {new_path}"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Return performance metrics"""
        return {
            'operation_counts': self.operation_counts.copy(),
            'latency_report': self.tracker.report() if self.tracker.metrics else {},
            'implementation': 'claude_official'
        }


# Helper function for creating tool results (as per official SDK)
def create_memory_tool_result(tool_use_id: str, content: str) -> Dict[str, Any]:
    """
    Create a properly formatted tool result for the API.
    
    This matches the format expected by Anthropic's API.
    """
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content
    }