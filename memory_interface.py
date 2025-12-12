"""
Common interface for all memory implementations.

This allows us to swap implementations for testing and benchmarking.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List


class MemoryInterface(ABC):
    """Base interface that all memory implementations must follow"""
    
    @abstractmethod
    def __init__(self, base_path: str = "./memories"):
        """Initialize memory system with base path"""
        pass
    
    @abstractmethod
    def handle_tool_call(self, tool_input: Dict[str, Any]) -> str:
        """
        Handle a memory tool call.
        
        Args:
            tool_input: Dictionary with command and parameters
            
        Returns:
            Result string
        """
        pass
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """
        Get the tool definition for the API.
        
        Returns:
            Tool definition dictionary
        """
        pass
    
    @abstractmethod
    def view(self, path: str, view_range: Optional[List[int]] = None) -> str:
        """View directory or file contents"""
        pass
    
    @abstractmethod
    def create(self, path: str, file_text: str) -> str:
        """Create or overwrite a file"""
        pass
    
    @abstractmethod
    def str_replace(self, path: str, old_str: str, new_str: str) -> str:
        """Replace text in a file"""
        pass
    
    @abstractmethod
    def insert(self, path: str, insert_line: int, insert_text: str) -> str:
        """Insert text at a specific line"""
        pass
    
    @abstractmethod
    def delete(self, path: str) -> str:
        """Delete a file or directory"""
        pass
    
    @abstractmethod
    def rename(self, old_path: str, new_path: str) -> str:
        """Rename or move a file/directory"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for this implementation.
        
        Returns:
            Dictionary with metrics like operation counts, latencies, etc.
        """
        pass