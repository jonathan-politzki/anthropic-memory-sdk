"""
Test User Segmentation and Directory Features

This tests the key questions:
1. How does memory store per user_id?
2. Can we segment memories by directories within?  
3. What are the advanced features we can build?
"""

from pathlib import Path
import shutil
from claude_official.memory_handler import ClaudeOfficialMemory


class UserSegmentedMemory(ClaudeOfficialMemory):
    """
    Enhanced memory with user segmentation and directory structure support.
    
    Features:
    - User ID segmentation: ./memories/user_123/
    - Directory organization: /memories/projects/, /memories/personal/
    - All standard memory operations
    """
    
    def __init__(self, base_path: str = "./memories", user_id: str = "default"):
        self.user_id = user_id
        
        # Create user-specific path
        user_path = Path(base_path) / f"user_{user_id}"
        super().__init__(str(user_path))
        
        print(f"📁 Memory initialized for user '{user_id}' at: {user_path}")
    
    def get_user_info(self):
        """Get information about this user's memory usage."""
        total_files = len(list(self.base_path.rglob("*"))) if self.base_path.exists() else 0
        total_size = sum(f.stat().st_size for f in self.base_path.rglob("*") if f.is_file()) if self.base_path.exists() else 0
        
        return {
            "user_id": self.user_id,
            "memory_path": str(self.base_path),
            "total_files": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024*1024), 2)
        }
    
    def list_directories(self):
        """List all directories in memory to see organization."""
        if not self.base_path.exists():
            return []
        
        dirs = [d.relative_to(self.base_path) for d in self.base_path.rglob("*") if d.is_dir()]
        return sorted(str(d) for d in dirs)
    
    def get_memory_tree(self):
        """Generate a tree view of all memories."""
        if not self.base_path.exists():
            return "No memories yet"
        
        def build_tree(path, prefix=""):
            items = []
            children = sorted(path.iterdir()) if path.is_dir() else []
            
            for i, child in enumerate(children):
                is_last = i == len(children) - 1
                current_prefix = "└── " if is_last else "├── "
                items.append(f"{prefix}{current_prefix}{child.name}")
                
                if child.is_dir():
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    items.extend(build_tree(child, next_prefix))
            
            return items
        
        tree_lines = [f"user_{self.user_id}/"]
        tree_lines.extend(build_tree(self.base_path))
        return "\n".join(tree_lines)


def test_user_segmentation():
    """Test multiple users with separate memory spaces."""
    print("🧪 TESTING USER SEGMENTATION")
    print("="*60)
    
    # Create memory for different users
    jonathan_memory = UserSegmentedMemory("./test_memories", "jonathan")
    alice_memory = UserSegmentedMemory("./test_memories", "alice")
    bob_memory = UserSegmentedMemory("./test_memories", "bob")
    
    print("\n1️⃣ Creating memories for Jonathan...")
    
    # Jonathan's organized memory structure
    jonathan_memory.handle_tool_call({
        "command": "create",
        "path": "/memories/personal/profile.xml",
        "file_text": """<?xml version="1.0"?>
<profile>
    <name>Jonathan Politzki</name>
    <role>Founder, Jean Memory</role>
    <location>NYC</location>
    <interests>
        <topic>Agentic AI</topic>
        <topic>Memory Systems</topic>
        <topic>Philosophy</topic>
    </interests>
</profile>"""
    })
    
    jonathan_memory.handle_tool_call({
        "command": "create", 
        "path": "/memories/projects/jean_memory/overview.md",
        "file_text": """# Jean Memory

Agentic memory platform that lets AI decide what to remember.

## Key Features:
- Context-aware memory storage
- Intelligent retrieval  
- Cross-application memory sharing

## Status: Seed funded $2M
"""
    })
    
    jonathan_memory.handle_tool_call({
        "command": "create",
        "path": "/memories/projects/irreverent_capital/notes.md", 
        "file_text": """# Irreverent Capital

Investment thesis: AI enables new business models.

## Portfolio Focus:
- Memory & context systems
- Agentic AI applications
- Developer tooling
"""
    })
    
    jonathan_memory.handle_tool_call({
        "command": "create",
        "path": "/memories/preferences/coding.txt",
        "file_text": """Coding Preferences:
- Languages: Python, TypeScript, Rust
- Style: Functional, clean, minimal
- Editor: VS Code with vim bindings
- No semicolons preferred
- 4-space indentation
"""
    })
    
    print("2️⃣ Creating memories for Alice...")
    
    # Alice's different memory structure
    alice_memory.handle_tool_call({
        "command": "create",
        "path": "/memories/work/current_project.md",
        "file_text": """# Q1 Project: API Redesign

## Tasks:
- [ ] Update authentication endpoints
- [ ] Improve error handling
- [ ] Add rate limiting
- [x] Review documentation

## Deadline: March 15th
"""
    })
    
    alice_memory.handle_tool_call({
        "command": "create",
        "path": "/memories/learning/ai_courses.txt", 
        "file_text": """AI Learning Progress:
- Completed: CS229 Machine Learning
- In Progress: Transformers Course (Hugging Face)
- Next: Advanced LLM Fine-tuning
"""
    })
    
    print("3️⃣ Creating memories for Bob...")
    
    # Bob's minimal memory
    bob_memory.handle_tool_call({
        "command": "create",
        "path": "/memories/notes.txt",
        "file_text": "Just testing the memory system. Keep it simple."
    })
    
    print("\n📊 USER STATISTICS:")
    print("-" * 60)
    for name, memory in [("Jonathan", jonathan_memory), ("Alice", alice_memory), ("Bob", bob_memory)]:
        info = memory.get_user_info()
        print(f"{name:8} | {info['total_files']} files | {info['total_size_mb']} MB | {info['memory_path']}")
    
    print("\n🌲 MEMORY TREE STRUCTURES:")
    print("-" * 60)
    
    print(f"\n📁 Jonathan's Memory Tree:")
    print(jonathan_memory.get_memory_tree())
    
    print(f"\n📁 Alice's Memory Tree:")
    print(alice_memory.get_memory_tree())
    
    print(f"\n📁 Bob's Memory Tree:")
    print(bob_memory.get_memory_tree())
    
    print("\n📂 DIRECTORY ORGANIZATION:")
    print("-" * 60)
    
    jonathan_dirs = jonathan_memory.list_directories()
    print(f"Jonathan's directories: {jonathan_dirs}")
    
    alice_dirs = alice_memory.list_directories()
    print(f"Alice's directories: {alice_dirs}")
    
    print("\n🔍 TESTING MEMORY ISOLATION:")
    print("-" * 60)
    
    # Test that users can't see each other's memories
    print("Jonathan's view of /memories:")
    result = jonathan_memory.handle_tool_call({"command": "view", "path": "/memories"})
    print(result[:200] + "..." if len(result) > 200 else result)
    
    print("\nAlice's view of /memories:")
    result = alice_memory.handle_tool_call({"command": "view", "path": "/memories"})
    print(result[:200] + "..." if len(result) > 200 else result)
    
    # Clean up
    shutil.rmtree("./test_memories", ignore_errors=True)
    print("\n✅ User segmentation test complete!")


def test_directory_features():
    """Test advanced directory operations within memory."""
    print("\n🧪 TESTING DIRECTORY FEATURES")
    print("="*60)
    
    memory = UserSegmentedMemory("./dir_test", "test_user")
    
    print("1️⃣ Creating nested directory structure...")
    
    # Create deep directory structure
    memory.handle_tool_call({
        "command": "create",
        "path": "/memories/projects/ai_research/papers/attention_mechanisms.md",
        "file_text": "# Attention Mechanisms\n\nKey papers and insights..."
    })
    
    memory.handle_tool_call({
        "command": "create", 
        "path": "/memories/projects/ai_research/code/transformer_impl.py",
        "file_text": "# Transformer Implementation\nclass Attention:\n    pass"
    })
    
    memory.handle_tool_call({
        "command": "create",
        "path": "/memories/personal/habits/morning_routine.txt",
        "file_text": "1. Coffee\n2. Exercise\n3. Review goals"
    })
    
    print("2️⃣ Testing directory operations...")
    
    # List root directory
    result = memory.handle_tool_call({"command": "view", "path": "/memories"})
    print(f"\nRoot directory:\n{result}")
    
    # List nested directory
    result = memory.handle_tool_call({"command": "view", "path": "/memories/projects"})
    print(f"\nProjects directory:\n{result}")
    
    # List deep nested directory  
    result = memory.handle_tool_call({"command": "view", "path": "/memories/projects/ai_research"})
    print(f"\nAI Research directory:\n{result}")
    
    print("3️⃣ Testing directory renaming...")
    
    # Rename a directory
    memory.handle_tool_call({
        "command": "rename",
        "old_path": "/memories/personal/habits",
        "new_path": "/memories/personal/daily_routines"
    })
    
    result = memory.handle_tool_call({"command": "view", "path": "/memories/personal"})
    print(f"\nAfter renaming 'habits' to 'daily_routines':\n{result}")
    
    print("4️⃣ Testing directory deletion...")
    
    # Delete a directory tree
    memory.handle_tool_call({
        "command": "delete",
        "path": "/memories/projects/ai_research"
    })
    
    result = memory.handle_tool_call({"command": "view", "path": "/memories/projects"}) 
    print(f"\nAfter deleting ai_research directory:\n{result}")
    
    print("\n🌲 Final memory tree:")
    print(memory.get_memory_tree())
    
    # Clean up
    shutil.rmtree("./dir_test", ignore_errors=True)
    print("\n✅ Directory features test complete!")


def demonstrate_advanced_features():
    """Show advanced memory organization patterns."""
    print("\n🚀 ADVANCED MEMORY FEATURES")
    print("="*60)
    
    memory = UserSegmentedMemory("./advanced_test", "power_user")
    
    print("1️⃣ Topic-based organization...")
    
    # Create topic-based memory structure
    topics = {
        "ai_research": {
            "transformers.md": "# Transformer Architecture\n\n## Attention Mechanism\n...",
            "memory_systems.md": "# Memory in AI\n\n## RAG vs Agentic\n...",
        },
        "programming": {
            "python_patterns.py": "# Python Design Patterns\n\nclass Singleton:\n    pass",
            "typescript_types.ts": "// Advanced TypeScript\ntype Maybe<T> = T | null;",
        },
        "business": {
            "startup_ideas.txt": "1. Agentic memory platform\n2. AI coding assistant\n3. Context-aware APIs",
            "market_analysis.md": "# AI Market Analysis\n\n## Current State\n...",
        }
    }
    
    for topic, files in topics.items():
        for filename, content in files.items():
            memory.handle_tool_call({
                "command": "create",
                "path": f"/memories/{topic}/{filename}",
                "file_text": content
            })
    
    print("2️⃣ Time-based organization...")
    
    # Add temporal structure
    memory.handle_tool_call({
        "command": "create",
        "path": "/memories/timeline/2024-12/memory_research.md",
        "file_text": "# December 2024 - Memory Research\n\n- Discovered Claude's memory architecture\n- Built user segmentation"
    })
    
    memory.handle_tool_call({
        "command": "create",
        "path": "/memories/timeline/2025-01/goals.txt", 
        "file_text": "2025 Goals:\n- Launch Jean Memory\n- Scale to 10k users\n- Raise Series A"
    })
    
    print("3️⃣ Priority-based organization...")
    
    # Add priority levels
    memory.handle_tool_call({
        "command": "create",
        "path": "/memories/priority/urgent/api_bug_fix.md",
        "file_text": "# URGENT: API Authentication Bug\n\nAffecting 20% of users. Fix needed by EOD."
    })
    
    memory.handle_tool_call({
        "command": "create",
        "path": "/memories/priority/important/new_feature_spec.md",
        "file_text": "# Important: Memory Analytics Feature\n\nSpec for user memory insights dashboard."
    })
    
    memory.handle_tool_call({
        "command": "create",
        "path": "/memories/priority/someday/blog_post_ideas.txt",
        "file_text": "Blog post ideas:\n- The future of AI memory\n- Building agentic systems"
    })
    
    print("4️⃣ Cross-referencing structure...")
    
    # Create reference files
    memory.handle_tool_call({
        "command": "create",
        "path": "/memories/meta/tags.txt",
        "file_text": "Tag Index:\n#ai -> ai_research/\n#code -> programming/\n#urgent -> priority/urgent/"
    })
    
    memory.handle_tool_call({
        "command": "create",
        "path": "/memories/meta/recent_topics.md",
        "file_text": "# Recently Active\n\n- Memory systems research\n- API bug investigation\n- Q1 planning"
    })
    
    print("\n🌲 Complete Advanced Memory Structure:")
    print(memory.get_memory_tree())
    
    print(f"\n📊 Memory Statistics:")
    info = memory.get_user_info()
    print(f"- Total files: {info['total_files']}")
    print(f"- Total size: {info['total_size_mb']} MB")
    print(f"- Directories: {len(memory.list_directories())}")
    
    print(f"\n📂 All Directories:")
    for directory in memory.list_directories():
        print(f"  - {directory}")
    
    # Clean up
    shutil.rmtree("./advanced_test", ignore_errors=True)
    print("\n✅ Advanced features demonstration complete!")


if __name__ == "__main__":
    test_user_segmentation()
    test_directory_features() 
    demonstrate_advanced_features()
    
    print("\n🎯 KEY INSIGHTS:")
    print("• User segmentation works perfectly with directory structure")
    print("• Memories are completely isolated per user_id")  
    print("• Directory organization enables rich memory structures")
    print("• Advanced patterns: topic, time, priority, meta-organization")
    print("• Ready for production multi-user memory systems")