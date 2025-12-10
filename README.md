# Anthropic Memory Tool SDK

> **The Future of AI Memory: From RAG to Agentic Memory**

This SDK implements Anthropic's Memory Tool - a paradigm shift in how AI systems persist and retrieve information across conversations.

## 🚀 Why Agentic Memory?

Traditional RAG (Retrieval-Augmented Generation) is passive: you decide what to store and when to retrieve. **Agentic Memory is active**: Claude decides what's worth remembering, organizes it intelligently, and retrieves it contextually.

| Traditional RAG | Agentic Memory |
|-----------------|----------------|
| You index documents | Claude stores what matters |
| You query the database | Claude queries when needed |
| Static embeddings | Dynamic, evolving knowledge |
| Separate from conversation | Integrated into reasoning |
| Manual organization | Self-organizing |

## 📦 Installation

```bash
pip install -r requirements.txt
```

## 🔧 Quick Start

```python
from memory_tool import MemoryToolHandler
import anthropic

# Initialize
client = anthropic.Anthropic()
memory_handler = MemoryToolHandler("./memories")

# Make API call with memory tool
response = client.beta.messages.create(
    model="claude-sonnet-4-5-20250514",
    max_tokens=4096,
    betas=["context-management-2025-06-27"],
    tools=[memory_handler.get_tool_definition()],
    messages=[{"role": "user", "content": "Remember that my name is Jonathan"}],
)

# Handle tool calls
for block in response.content:
    if block.type == "tool_use":
        result = memory_handler.handle_tool_call(block.input)
        print(f"Memory operation result: {result}")
```

## 🎮 Run the Demo

```bash
export ANTHROPIC_API_KEY='your-api-key'
python demo.py
```

The demo includes:
1. **Basic Memory** - Store project information
2. **Memory Recall** - Retrieve stored information
3. **Learning from Feedback** - Save coding preferences
4. **Complex Task** - Use memory to inform responses
5. **Interactive Mode** - Chat freely with memory-enabled Claude

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│                 │     │                  │     │                 │
│   Your App      │────▶│   Claude API     │────▶│   Memory Tool   │
│                 │     │   (with Memory)  │     │   Handler       │
│                 │◀────│                  │◀────│                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                                 ┌─────────────────┐
                                                 │   ./memories/   │
                                                 │                 │
                                                 │  ├─ project.xml │
                                                 │  ├─ prefs.txt   │
                                                 │  └─ notes/      │
                                                 └─────────────────┘
```

## 📝 Memory Commands

The memory tool supports these operations:

### `view` - Read files or directories
```python
{"command": "view", "path": "/memories"}
{"command": "view", "path": "/memories/notes.txt", "view_range": [1, 10]}
```

### `create` - Create or overwrite files
```python
{"command": "create", "path": "/memories/notes.txt", "file_text": "My notes..."}
```

### `str_replace` - Replace text in files
```python
{"command": "str_replace", "path": "/memories/prefs.txt", "old_str": "blue", "new_str": "green"}
```

### `insert` - Insert text at a line
```python
{"command": "insert", "path": "/memories/todo.txt", "insert_line": 2, "insert_text": "New item"}
```

### `delete` - Delete files or directories
```python
{"command": "delete", "path": "/memories/old_file.txt"}
```

### `rename` - Move or rename files
```python
{"command": "rename", "old_path": "/memories/draft.txt", "new_path": "/memories/final.txt"}
```

## 🔒 Security

The `MemoryToolHandler` includes built-in security measures:

- **Path Traversal Protection**: All paths are validated to prevent `../` attacks
- **Sandboxed Directory**: Operations restricted to the memories directory
- **Input Validation**: All inputs are validated before execution

## 🔄 Agentic Loop Pattern

Here's the core pattern for building with the memory tool:

```python
def agentic_loop(client, memory_handler, messages):
    while True:
        # 1. Call Claude with memory tool
        response = client.beta.messages.create(
            model="claude-sonnet-4-5-20250514",
            betas=["context-management-2025-06-27"],
            tools=[memory_handler.get_tool_definition()],
            messages=messages,
        )
        
        # 2. If done, return response
        if response.stop_reason == "end_turn":
            return extract_text(response)
        
        # 3. Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = memory_handler.handle_tool_call(block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })
        
        # 4. Add results and continue
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
```

## 🧠 How Claude Uses Memory

When you enable the memory tool, Claude automatically:

1. **Checks memory first**: Before starting any task, Claude views `/memories` to check for relevant context
2. **Stores what matters**: Important information, preferences, and progress are saved
3. **Organizes intelligently**: Claude creates structured files (often XML) to organize information
4. **Recalls contextually**: When relevant, Claude retrieves and uses stored information

## 🎯 Use Cases

- **Project Context**: Maintain context across agent executions
- **Learning Preferences**: Remember coding style, communication preferences
- **Progress Tracking**: Resume complex tasks after context resets
- **Knowledge Building**: Accumulate domain knowledge over time
- **Cross-Conversation Learning**: Improve at recurring workflows

## 📚 Advanced: Context Editing

Combine memory with context editing for long-running workflows:

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-5-20250514",
    betas=["context-management-2025-06-27"],
    tools=[memory_handler.get_tool_definition()],
    messages=messages,
    context_management={
        "edits": [{
            "type": "clear_tool_uses_20250919",
            "trigger": {"type": "input_tokens", "value": 100000},
            "keep": {"type": "tool_uses", "value": 3},
            "exclude_tools": ["memory"]  # Keep memory operations visible
        }]
    }
)
```

This automatically clears old tool results when approaching context limits, while preserving memory operations.

## 🌟 The Vision

We believe the future of AI memory is:

- **Agentic**: AI decides what to remember and when
- **Persistent**: Knowledge builds over time
- **Contextual**: Memories are retrieved when relevant
- **Organized**: Self-structuring knowledge base
- **Evolving**: Memories update and improve

This is just the beginning. Welcome to the future of AI memory.

---

Built with ❤️ for the agentic AI future

