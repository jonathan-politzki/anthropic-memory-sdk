"""
Advanced Memory Implementation

Our vision for next-generation agentic memory with:
- Memory blocks (working, archival, persona)
- Background reorganization
- Smart routing based on context
- Overflow to RAG when needed
- Predictive pre-fetching
"""

import os
import json
import asyncio
import shutil
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import OrderedDict, defaultdict
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import sys
sys.path.append('..')
from memory_interface import MemoryInterface
from latency_benchmark import LatencyTracker, OperationType


class MemoryTier(Enum):
    """Memory tier levels"""
    WORKING = "working"      # Hot cache, <4KB, immediate access
    ARCHIVAL = "archival"    # Warm store, <100KB, important persistent
    OVERFLOW = "overflow"    # Cold storage, unlimited, RAG-indexed


@dataclass
class MemoryBlock:
    """A block of memory with metadata"""
    content: str
    tier: MemoryTier
    access_count: int = 0
    last_access: float = 0
    importance_score: float = 0.5
    created_at: float = 0
    size_bytes: int = 0
    
    def update_access(self):
        """Update access statistics"""
        self.access_count += 1
        self.last_access = datetime.now().timestamp()


class AdvancedMemory(MemoryInterface):
    """
    Advanced memory implementation with our improvements:
    - Tiered storage (working → archival → overflow)
    - Smart routing based on access patterns
    - Background reorganization
    - Predictive pre-fetching
    """
    
    # Size limits per tier
    TIER_LIMITS = {
        MemoryTier.WORKING: 4096,      # 4KB
        MemoryTier.ARCHIVAL: 102400,   # 100KB
        MemoryTier.OVERFLOW: float('inf')
    }
    
    # Latency targets per tier (ms)
    LATENCY_TARGETS = {
        MemoryTier.WORKING: 10,
        MemoryTier.ARCHIVAL: 50,
        MemoryTier.OVERFLOW: 200
    }
    
    def __init__(self, base_path: str = "./memories"):
        """Initialize advanced memory system"""
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create tier directories
        self.tier_paths = {}
        for tier in MemoryTier:
            tier_path = self.base_path / tier.value
            tier_path.mkdir(exist_ok=True)
            self.tier_paths[tier] = tier_path
        
        # Latency tracking
        self.tracker = LatencyTracker(str(self.base_path))
        
        # Memory blocks by tier
        self.memory_blocks: Dict[MemoryTier, Dict[str, MemoryBlock]] = {
            tier: {} for tier in MemoryTier
        }
        
        # Access pattern learning
        self.access_patterns = defaultdict(list)  # path -> [timestamps]
        self.predicted_next = set()  # Paths likely to be accessed next
        
        # Operation counts
        self.operation_counts = defaultdict(int)
        
        # Load existing memories into tiers
        self._load_memories()
        
        # Start background reorganization (would be async in production)
        self.reorganize_counter = 0
        self.reorganize_threshold = 10  # Reorganize every N operations
    
    def get_tool_definition(self) -> Dict[str, Any]:
        """Tool definition - compatible with Claude"""
        return {
            "type": "memory_20250818",
            "name": "memory"
        }
    
    def _load_memories(self):
        """Load existing memories into appropriate tiers"""
        for tier in MemoryTier:
            tier_path = self.tier_paths[tier]
            for file_path in tier_path.glob("*"):
                if file_path.is_file():
                    rel_path = file_path.name
                    content = file_path.read_text(encoding="utf-8")
                    
                    block = MemoryBlock(
                        content=content,
                        tier=tier,
                        created_at=file_path.stat().st_ctime,
                        last_access=file_path.stat().st_atime,
                        size_bytes=len(content)
                    )
                    
                    self.memory_blocks[tier][rel_path] = block
    
    def _determine_tier(self, path: str, content: str) -> MemoryTier:
        """Determine which tier a memory belongs to"""
        size = len(content)
        
        # Check access patterns
        if path in self.access_patterns:
            recent_accesses = len([
                t for t in self.access_patterns[path]
                if datetime.now().timestamp() - t < 300  # Last 5 minutes
            ])
            
            if recent_accesses > 3:
                return MemoryTier.WORKING
        
        # Size-based allocation
        if size <= self.TIER_LIMITS[MemoryTier.WORKING]:
            # Check if working tier has space
            working_size = sum(b.size_bytes for b in self.memory_blocks[MemoryTier.WORKING].values())
            if working_size + size <= self.TIER_LIMITS[MemoryTier.WORKING]:
                return MemoryTier.WORKING
        
        if size <= self.TIER_LIMITS[MemoryTier.ARCHIVAL]:
            return MemoryTier.ARCHIVAL
        
        return MemoryTier.OVERFLOW
    
    def _predict_next_access(self, current_path: str):
        """Predict what might be accessed next based on patterns"""
        self.predicted_next.clear()
        
        # Simple prediction: files often accessed together
        if current_path in self.access_patterns:
            # Find files accessed within 10 seconds of this one
            current_times = self.access_patterns[current_path]
            if current_times:
                last_time = current_times[-1]
                
                for other_path, times in self.access_patterns.items():
                    if other_path != current_path:
                        for t in times:
                            if abs(t - last_time) < 10:  # Within 10 seconds
                                self.predicted_next.add(other_path)
                                break
    
    def _reorganize_if_needed(self):
        """Trigger reorganization periodically"""
        self.reorganize_counter += 1
        
        if self.reorganize_counter >= self.reorganize_threshold:
            self._reorganize_memories()
            self.reorganize_counter = 0
    
    def _reorganize_memories(self):
        """Reorganize memories between tiers based on usage"""
        now = datetime.now().timestamp()
        
        # Promote frequently accessed from archival to working
        for path, block in list(self.memory_blocks[MemoryTier.ARCHIVAL].items()):
            if block.access_count > 5 and (now - block.last_access) < 300:
                # Check if working tier has space
                working_size = sum(b.size_bytes for b in self.memory_blocks[MemoryTier.WORKING].values())
                if working_size + block.size_bytes <= self.TIER_LIMITS[MemoryTier.WORKING]:
                    # Promote to working
                    self._move_between_tiers(path, MemoryTier.ARCHIVAL, MemoryTier.WORKING)
        
        # Demote old items from working to archival
        for path, block in list(self.memory_blocks[MemoryTier.WORKING].items()):
            if (now - block.last_access) > 600:  # Not accessed in 10 minutes
                self._move_between_tiers(path, MemoryTier.WORKING, MemoryTier.ARCHIVAL)
        
        # Move very old items to overflow
        for path, block in list(self.memory_blocks[MemoryTier.ARCHIVAL].items()):
            if (now - block.last_access) > 3600:  # Not accessed in 1 hour
                self._move_between_tiers(path, MemoryTier.ARCHIVAL, MemoryTier.OVERFLOW)
    
    def _move_between_tiers(self, path: str, from_tier: MemoryTier, to_tier: MemoryTier):
        """Move a memory block between tiers"""
        if path not in self.memory_blocks[from_tier]:
            return
        
        block = self.memory_blocks[from_tier].pop(path)
        block.tier = to_tier
        self.memory_blocks[to_tier][path] = block
        
        # Move physical file
        from_path = self.tier_paths[from_tier] / path
        to_path = self.tier_paths[to_tier] / path
        
        if from_path.exists():
            to_path.write_text(block.content, encoding="utf-8")
            from_path.unlink()
    
    def _validate_path(self, path: str) -> Tuple[str, Path]:
        """Validate path and return clean name + full path"""
        if path.startswith("/memories"):
            path = path[9:]
        if path.startswith("/"):
            path = path[1:]
        
        # For advanced memory, we use flat structure in tiers
        clean_name = path.replace("/", "_")
        
        return clean_name, self.base_path
    
    def _find_in_tiers(self, clean_name: str) -> Optional[Tuple[MemoryTier, MemoryBlock]]:
        """Find a memory across all tiers"""
        # Check predicted set first (optimization)
        if clean_name in self.predicted_next:
            for tier in [MemoryTier.WORKING, MemoryTier.ARCHIVAL]:
                if clean_name in self.memory_blocks[tier]:
                    return tier, self.memory_blocks[tier][clean_name]
        
        # Check each tier in order of likelihood
        for tier in MemoryTier:
            if clean_name in self.memory_blocks[tier]:
                return tier, self.memory_blocks[tier][clean_name]
        
        return None
    
    def handle_tool_call(self, tool_input: Dict[str, Any]) -> str:
        """Handle tool call with smart routing"""
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
            
            # Periodic reorganization
            self._reorganize_if_needed()
            
            return result
        except Exception as e:
            return f"Error: {str(e)}"
    
    def _handle_view(self, input_data: Dict[str, Any]) -> str:
        """Smart view with tier awareness"""
        path = input_data.get("path", "/memories")
        view_range = input_data.get("view_range")
        
        return self.view(path, view_range)
    
    def view(self, path: str, view_range: Optional[List[int]] = None) -> str:
        """View with smart routing across tiers"""
        clean_name, base = self._validate_path(path)
        
        # Handle root directory listing
        if path in ["/memories", ""]:
            items = []
            
            # Show items from all tiers with tier indicator
            for tier in MemoryTier:
                for name, block in self.memory_blocks[tier].items():
                    tier_indicator = {
                        MemoryTier.WORKING: "🔥",   # Hot
                        MemoryTier.ARCHIVAL: "📚",  # Warm
                        MemoryTier.OVERFLOW: "🧊"   # Cold
                    }[tier]
                    
                    items.append(f"{tier_indicator} {name} ({block.size_bytes}B, tier: {tier.value})")
            
            if not items:
                return "Directory: /memories\n(empty)"
            
            return f"Directory: /memories\n" + "\n".join(sorted(items))
        
        # Find file in tiers
        result = self._find_in_tiers(clean_name)
        if not result:
            return f"Error: Path does not exist: {path}"
        
        tier, block = result
        
        # Update access statistics
        block.update_access()
        self.access_patterns[clean_name].append(datetime.now().timestamp())
        
        # Predict next access
        self._predict_next_access(clean_name)
        
        # Track tier-specific latency
        self.operation_counts[f'view_{tier.value}'] += 1
        
        content = block.content
        if view_range:
            lines = content.splitlines()
            start, end = view_range
            start = max(0, start - 1)
            end = min(len(lines), end)
            return "\n".join(lines[start:end])
        
        return content
    
    def create(self, path: str, file_text: str) -> str:
        """Create with intelligent tier placement"""
        clean_name, base = self._validate_path(path)
        
        # Determine appropriate tier
        tier = self._determine_tier(clean_name, file_text)
        
        # Create memory block
        block = MemoryBlock(
            content=file_text,
            tier=tier,
            created_at=datetime.now().timestamp(),
            last_access=datetime.now().timestamp(),
            size_bytes=len(file_text)
        )
        
        # Store in tier
        self.memory_blocks[tier][clean_name] = block
        
        # Write to filesystem
        tier_path = self.tier_paths[tier] / clean_name
        tier_path.write_text(file_text, encoding="utf-8")
        
        return f"Created file: {path} (tier: {tier.value})"
    
    def str_replace(self, path: str, old_str: str, new_str: str) -> str:
        """Replace with tier management"""
        clean_name, base = self._validate_path(path)
        
        result = self._find_in_tiers(clean_name)
        if not result:
            return f"Error: File does not exist: {path}"
        
        tier, block = result
        
        if old_str not in block.content:
            return "Error: String not found in file"
        
        count = block.content.count(old_str)
        block.content = block.content.replace(old_str, new_str)
        block.size_bytes = len(block.content)
        block.update_access()
        
        # Check if tier change needed due to size
        new_tier = self._determine_tier(clean_name, block.content)
        if new_tier != tier:
            self._move_between_tiers(clean_name, tier, new_tier)
            tier = new_tier
        
        # Write to filesystem
        tier_path = self.tier_paths[tier] / clean_name
        tier_path.write_text(block.content, encoding="utf-8")
        
        return f"Replaced {count} occurrence(s) in {path}"
    
    def insert(self, path: str, insert_line: int, insert_text: str) -> str:
        """Insert with tier awareness"""
        clean_name, base = self._validate_path(path)
        
        result = self._find_in_tiers(clean_name)
        
        if not result:
            if insert_line == 0:
                return self.create(path, insert_text)
            return f"Error: Cannot insert at line {insert_line} in non-existent file"
        
        tier, block = result
        lines = block.content.splitlines()
        
        if insert_line < 0:
            return "Error: Line number must be non-negative"
        
        while len(lines) < insert_line:
            lines.append("")
        
        lines.insert(insert_line, insert_text)
        block.content = "\n".join(lines)
        block.size_bytes = len(block.content)
        block.update_access()
        
        # Check tier change
        new_tier = self._determine_tier(clean_name, block.content)
        if new_tier != tier:
            self._move_between_tiers(clean_name, tier, new_tier)
            tier = new_tier
        
        # Write to filesystem
        tier_path = self.tier_paths[tier] / clean_name
        tier_path.write_text(block.content, encoding="utf-8")
        
        return f"Inserted text at line {insert_line} in {path}"
    
    def delete(self, path: str) -> str:
        """Delete from appropriate tier"""
        clean_name, base = self._validate_path(path)
        
        result = self._find_in_tiers(clean_name)
        if not result:
            return f"Error: Path does not exist: {path}"
        
        tier, block = result
        
        # Remove from memory
        del self.memory_blocks[tier][clean_name]
        
        # Remove from filesystem
        tier_path = self.tier_paths[tier] / clean_name
        if tier_path.exists():
            tier_path.unlink()
        
        # Clean up patterns
        self.access_patterns.pop(clean_name, None)
        self.predicted_next.discard(clean_name)
        
        return f"Deleted file: {path}"
    
    def rename(self, old_path: str, new_path: str) -> str:
        """Rename across tiers"""
        old_name, _ = self._validate_path(old_path)
        new_name, _ = self._validate_path(new_path)
        
        result = self._find_in_tiers(old_name)
        if not result:
            return f"Error: Source path does not exist: {old_path}"
        
        tier, block = result
        
        # Check if destination exists
        if self._find_in_tiers(new_name):
            return f"Error: Destination already exists: {new_path}"
        
        # Move in memory
        del self.memory_blocks[tier][old_name]
        self.memory_blocks[tier][new_name] = block
        
        # Move on filesystem
        old_tier_path = self.tier_paths[tier] / old_name
        new_tier_path = self.tier_paths[tier] / new_name
        
        if old_tier_path.exists():
            old_tier_path.rename(new_tier_path)
        
        # Update patterns
        if old_name in self.access_patterns:
            self.access_patterns[new_name] = self.access_patterns.pop(old_name)
        
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
        """Return advanced metrics"""
        tier_stats = {}
        for tier in MemoryTier:
            blocks = self.memory_blocks[tier]
            total_size = sum(b.size_bytes for b in blocks.values())
            
            tier_stats[tier.value] = {
                'count': len(blocks),
                'total_size_bytes': total_size,
                'utilization': round(total_size / self.TIER_LIMITS[tier] * 100, 1) if self.TIER_LIMITS[tier] != float('inf') else 0
            }
        
        # Calculate hit rates by tier
        total_views = sum(self.operation_counts.get(f'view_{tier.value}', 0) for tier in MemoryTier)
        tier_hit_rates = {}
        if total_views > 0:
            for tier in MemoryTier:
                hits = self.operation_counts.get(f'view_{tier.value}', 0)
                tier_hit_rates[tier.value] = round(hits / total_views * 100, 1)
        
        return {
            'operation_counts': dict(self.operation_counts),
            'tier_statistics': tier_stats,
            'tier_hit_rates': tier_hit_rates,
            'predicted_next_count': len(self.predicted_next),
            'reorganizations': self.reorganize_counter,
            'latency_report': self.tracker.report() if self.tracker.metrics else {},
            'implementation': 'advanced_memory'
        }