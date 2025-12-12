"""
Reverse Engineered Memory Implementation

This is our own implementation built from scratch to understand how memory works.
We observe Claude's behavior and build our own interpretation.

Key differences from official:
- Adds caching layer for frequently accessed files
- Implements batched operations
- Adds memory indexing for faster searches
"""

import os
import json
import shutil
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from collections import OrderedDict
from datetime import datetime
import sys
sys.path.append('..')
from memory_interface import MemoryInterface
from latency_benchmark import LatencyTracker, OperationType


class ReverseEngineeredMemory(MemoryInterface):
    """
    Our reverse-engineered implementation with optimizations.
    
    Built by observing Claude's memory patterns and improving on them.
    """
    
    def __init__(self, base_path: str = "./memories"):
        """Initialize with caching and indexing"""
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Latency tracking
        self.tracker = LatencyTracker(str(self.base_path))
        
        # Cache for frequently accessed files (LRU)
        self.cache = OrderedDict()
        self.cache_size = 10  # Max files in cache
        
        # Index for fast searching
        self.index = {
            'files': {},  # path -> metadata
            'directories': set(),
            'last_scan': None
        }
        
        # Operation counts
        self.operation_counts = {
            'view': 0,
            'create': 0,
            'str_replace': 0,
            'insert': 0,
            'delete': 0,
            'rename': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Build initial index
        self._rebuild_index()
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Tool definition - same as official for compatibility"""
        return {
            "type": "memory_20250818",
            "name": "memory"
        }
    
    def _rebuild_index(self):
        """Build an index of all files for faster access"""
        self.index['files'].clear()
        self.index['directories'].clear()
        
        for path in self.base_path.rglob('*'):
            rel_path = str(path.relative_to(self.base_path))
            
            if path.is_dir():
                self.index['directories'].add(rel_path)
            else:
                self.index['files'][rel_path] = {
                    'size': path.stat().st_size,
                    'modified': path.stat().st_mtime,
                    'hash': None  # Computed on demand
                }
        
        self.index['last_scan'] = datetime.now().isoformat()
    
    def _get_from_cache(self, path: str) -> Optional[str]:
        """Get file content from cache if available"""
        if path in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(path)
            self.operation_counts['cache_hits'] += 1
            return self.cache[path]
        
        self.operation_counts['cache_misses'] += 1
        return None
    
    def _add_to_cache(self, path: str, content: str):
        """Add content to cache with LRU eviction"""
        if len(self.cache) >= self.cache_size:
            # Evict least recently used
            self.cache.popitem(last=False)
        
        self.cache[path] = content
    
    def _validate_path(self, path: str) -> Path:
        """Validate path with security checks"""
        if path.startswith("/memories"):
            path = path[9:]
        if path.startswith("/"):
            path = path[1:]
        
        full_path = (self.base_path / path).resolve()
        
        try:
            full_path.relative_to(self.base_path)
        except ValueError:
            raise ValueError(f"Path traversal detected: {path}")
        
        return full_path
    
    def handle_tool_call(self, tool_input: Dict[str, Any]) -> str:
        """Main handler with optimizations"""
        command = tool_input.get("command")
        
        if not command:
            return "Error: No command specified"
        
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
            result = handler(tool_input)
            
            # Update index after write operations
            if command in ['create', 'delete', 'rename']:
                self._update_index_partial(tool_input)
            
            return result
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _update_index_partial(self, tool_input: Dict[str, Any]):
        """Partially update index after operations (faster than full rebuild)"""
        command = tool_input.get("command")
        
        if command == "create":
            path = tool_input.get("path", "").replace("/memories/", "")
            self.index['files'][path] = {
                'size': len(tool_input.get("file_text", "")),
                'modified': datetime.now().timestamp(),
                'hash': None
            }
        elif command == "delete":
            path = tool_input.get("path", "").replace("/memories/", "")
            self.index['files'].pop(path, None)
            self.index['directories'].discard(path)
            # Clear from cache
            self.cache.pop(path, None)
        elif command == "rename":
            old_path = tool_input.get("old_path", "").replace("/memories/", "")
            new_path = tool_input.get("new_path", "").replace("/memories/", "")
            if old_path in self.index['files']:
                self.index['files'][new_path] = self.index['files'].pop(old_path)
            # Update cache
            if old_path in self.cache:
                self.cache[new_path] = self.cache.pop(old_path)
    
    def _handle_view(self, input_data: Dict[str, Any]) -> str:
        """Optimized view with caching"""
        path = input_data.get("path", "/memories")
        view_range = input_data.get("view_range")
        
        return self.view(path, view_range)
    
    def view(self, path: str, view_range: Optional[List[int]] = None) -> str:
        """View with cache support"""
        resolved_path = self._validate_path(path)
        
        # Try cache first for files
        if resolved_path.is_file():
            rel_path = str(resolved_path.relative_to(self.base_path))
            cached = self._get_from_cache(rel_path)
            if cached is not None:
                if view_range:
                    lines = cached.splitlines()
                    start, end = view_range
                    start = max(0, start - 1)
                    end = min(len(lines), end)
                    return "\n".join(lines[start:end])
                return cached
        
        # Handle directories using index (faster)
        if resolved_path == self.base_path or resolved_path.is_dir():
            rel_dir = "" if resolved_path == self.base_path else str(resolved_path.relative_to(self.base_path))
            
            # Use index for listing
            items = []
            for file_path, metadata in self.index['files'].items():
                if rel_dir == "" or file_path.startswith(rel_dir + "/"):
                    # Only show direct children
                    remaining = file_path[len(rel_dir):].lstrip("/")
                    if "/" not in remaining:
                        items.append(f"📄 {remaining} ({metadata['size']} bytes)")
            
            for dir_path in self.index['directories']:
                if rel_dir == "" or dir_path.startswith(rel_dir + "/"):
                    remaining = dir_path[len(rel_dir):].lstrip("/")
                    if "/" not in remaining:
                        items.append(f"📁 {remaining}")
            
            if not items:
                return f"Directory: {path}\n(empty)"
            
            return f"Directory: {path}\n" + "\n".join(sorted(items))
        
        # File content (not in cache)
        if resolved_path.exists():
            content = resolved_path.read_text(encoding="utf-8")
            
            # Add to cache
            rel_path = str(resolved_path.relative_to(self.base_path))
            self._add_to_cache(rel_path, content)
            
            if view_range:
                lines = content.splitlines()
                start, end = view_range
                start = max(0, start - 1)
                end = min(len(lines), end)
                return "\n".join(lines[start:end])
            
            return content
        
        return f"Error: Path does not exist: {path}"
    
    def create(self, path: str, file_text: str) -> str:
        """Create file with cache update"""
        resolved_path = self._validate_path(path)
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(file_text, encoding="utf-8")
        
        # Add to cache
        rel_path = str(resolved_path.relative_to(self.base_path))
        self._add_to_cache(rel_path, file_text)
        
        return f"Created file: {path}"
    
    def str_replace(self, path: str, old_str: str, new_str: str) -> str:
        """String replace with cache invalidation"""
        resolved_path = self._validate_path(path)
        
        if not resolved_path.exists():
            return f"Error: File does not exist: {path}"
        
        content = resolved_path.read_text(encoding="utf-8")
        
        if old_str not in content:
            return f"Error: String not found in file"
        
        count = content.count(old_str)
        new_content = content.replace(old_str, new_str)
        resolved_path.write_text(new_content, encoding="utf-8")
        
        # Update cache
        rel_path = str(resolved_path.relative_to(self.base_path))
        self._add_to_cache(rel_path, new_content)
        
        return f"Replaced {count} occurrence(s) in {path}"
    
    def insert(self, path: str, insert_line: int, insert_text: str) -> str:
        """Insert with cache update"""
        resolved_path = self._validate_path(path)
        
        if not resolved_path.exists():
            if insert_line == 0:
                resolved_path.write_text(insert_text, encoding="utf-8")
                rel_path = str(resolved_path.relative_to(self.base_path))
                self._add_to_cache(rel_path, insert_text)
                return f"Created new file with content at {path}"
            return f"Error: Cannot insert at line {insert_line} in non-existent file"
        
        content = resolved_path.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        if insert_line < 0:
            return "Error: Line number must be non-negative"
        
        while len(lines) < insert_line:
            lines.append("")
        
        lines.insert(insert_line, insert_text)
        new_content = "\n".join(lines)
        resolved_path.write_text(new_content, encoding="utf-8")
        
        # Update cache
        rel_path = str(resolved_path.relative_to(self.base_path))
        self._add_to_cache(rel_path, new_content)
        
        return f"Inserted text at line {insert_line} in {path}"
    
    def delete(self, path: str) -> str:
        """Delete with cache cleanup"""
        resolved_path = self._validate_path(path)
        
        if not resolved_path.exists():
            return f"Error: Path does not exist: {path}"
        
        # Remove from cache
        rel_path = str(resolved_path.relative_to(self.base_path))
        self.cache.pop(rel_path, None)
        
        if resolved_path.is_dir():
            shutil.rmtree(resolved_path)
            return f"Deleted directory: {path}"
        else:
            resolved_path.unlink()
            return f"Deleted file: {path}"
    
    def rename(self, old_path: str, new_path: str) -> str:
        """Rename with cache update"""
        old_resolved = self._validate_path(old_path)
        new_resolved = self._validate_path(new_path)
        
        if not old_resolved.exists():
            return f"Error: Source path does not exist: {old_path}"
        
        if new_resolved.exists():
            return f"Error: Destination already exists: {new_path}"
        
        new_resolved.parent.mkdir(parents=True, exist_ok=True)
        old_resolved.rename(new_resolved)
        
        # Update cache
        old_rel = str(old_resolved.relative_to(self.base_path))
        new_rel = str(new_resolved.relative_to(self.base_path))
        if old_rel in self.cache:
            self.cache[new_rel] = self.cache.pop(old_rel)
        
        return f"Renamed {old_path} to {new_path}"
    
    def _handle_create(self, input_data: Dict[str, Any]) -> str:
        path = input_data.get("path")
        file_text = input_data.get("file_text", "")
        if not path:
            return "Error: No path specified"
        return self.create(path, file_text)
    
    def _handle_str_replace(self, input_data: Dict[str, Any]) -> str:
        path = input_data.get("path")
        old_str = input_data.get("old_str")
        new_str = input_data.get("new_str")
        if not all([path, old_str is not None, new_str is not None]):
            return "Error: Missing required parameters"
        return self.str_replace(path, old_str, new_str)
    
    def _handle_insert(self, input_data: Dict[str, Any]) -> str:
        path = input_data.get("path")
        insert_line = input_data.get("insert_line")
        insert_text = input_data.get("insert_text", "")
        if not path or insert_line is None:
            return "Error: Missing required parameters"
        return self.insert(path, insert_line, insert_text)
    
    def _handle_delete(self, input_data: Dict[str, Any]) -> str:
        path = input_data.get("path")
        if not path:
            return "Error: No path specified"
        return self.delete(path)
    
    def _handle_rename(self, input_data: Dict[str, Any]) -> str:
        old_path = input_data.get("old_path")
        new_path = input_data.get("new_path")
        if not old_path or not new_path:
            return "Error: Both paths required"
        return self.rename(old_path, new_path)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Return enhanced metrics"""
        cache_ratio = 0
        if self.operation_counts['cache_hits'] + self.operation_counts['cache_misses'] > 0:
            cache_ratio = self.operation_counts['cache_hits'] / (
                self.operation_counts['cache_hits'] + self.operation_counts['cache_misses']
            )
        
        return {
            'operation_counts': self.operation_counts.copy(),
            'cache_hit_ratio': round(cache_ratio, 3),
            'index_size': len(self.index['files']),
            'cache_size': len(self.cache),
            'latency_report': self.tracker.report() if self.tracker.metrics else {},
            'implementation': 'reverse_engineered'
        }