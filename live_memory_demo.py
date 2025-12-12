"""
Live Memory Demo - See how Claude actually uses memory in conversation

This creates a real conversation with Claude using memory to show:
1. What Claude decides to store
2. How it organizes information  
3. When it recalls memories
4. How memory persists across sessions
"""

import os
import anthropic
from claude_official.memory_handler import ClaudeOfficialMemory, create_memory_tool_result


def run_conversation_with_memory(messages, memory_handler, max_turns=10):
    """Run a conversation with memory, showing each step"""
    
    client = anthropic.Anthropic()
    
    for turn in range(max_turns):
        print(f"\n{'='*80}")
        print(f"🔄 TURN {turn + 1}")
        print('='*80)
        
        # Show current memory state before Claude responds
        memory_content = memory_handler.handle_tool_call({"command": "view", "path": "/memories"})
        print(f"📂 Current memory state:\n{memory_content}\n")
        
        # Make API call with memory tool
        response = client.beta.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            tools=[memory_handler.get_tool_definition()],
            messages=messages,
            betas=["context-management-2025-06-27"],
            context_management={
                "edits": [{
                    "type": "clear_tool_uses_20250919",
                    "trigger": { "type": "input_tokens", "value": 20000 },
                    "keep": { "type": "tool_uses", "value": 3 }
                }]
            }
        )
        
        print(f"🤖 Claude's response:")
        
        # Check if Claude is done
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"   {block.text}")
            return
        
        # Process tool uses and Claude's messages
        tool_results = []
        assistant_content = []
        
        for block in response.content:
            assistant_content.append(block)
            
            if block.type == "text":
                print(f"   💬 {block.text}")
            
            elif block.type == "tool_use":
                print(f"\n   🔧 MEMORY OPERATION: {block.name}")
                print(f"      📥 Input: {block.input}")
                
                # Execute memory operation
                result = memory_handler.handle_tool_call(block.input)
                print(f"      📤 Result: {result}")
                
                tool_results.append(create_memory_tool_result(block.id, result))
        
        # Add to conversation history
        messages.append({"role": "assistant", "content": assistant_content})
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
    
    print(f"\n⚠️ Reached max turns ({max_turns})")


def demo_1_initial_conversation():
    """Demo 1: First conversation - see what Claude decides to remember"""
    print("\n" + "="*100)
    print("🎬 DEMO 1: Initial Conversation - What Does Claude Choose to Remember?")
    print("="*100)
    
    # Fresh memory
    memory = ClaudeOfficialMemory("./demo_memories_1")
    
    messages = [
        {
            "role": "user", 
            "content": """Hi! I'm Jonathan, a software engineer working on AI memory systems. 

I'm currently building a startup that focuses on agentic memory - letting AI decide what to remember rather than using traditional RAG. I live in San Francisco and I'm really interested in how Claude's memory tool works.

My coding preferences:
- I love Python and TypeScript  
- I prefer functional programming when possible
- I like clean, minimal code
- I use VS Code with vim bindings

Can you help me understand how your memory system works? What do you think is worth remembering from what I just told you?"""
        }
    ]
    
    run_conversation_with_memory(messages, memory)


def demo_2_memory_recall():
    """Demo 2: New session - does Claude recall previous memories?"""
    print("\n" + "="*100)
    print("🎬 DEMO 2: Memory Recall - Does Claude Remember Me?")
    print("="*100)
    
    # Same memory directory as demo 1
    memory = ClaudeOfficialMemory("./demo_memories_1")
    
    messages = [
        {
            "role": "user",
            "content": """Hey! Can you help me write a quick function to parse JSON? 

Make sure to follow my coding preferences if you remember them."""
        }
    ]
    
    run_conversation_with_memory(messages, memory)


def demo_3_memory_evolution():
    """Demo 3: See how memory evolves with new information"""
    print("\n" + "="*100)
    print("🎬 DEMO 3: Memory Evolution - How Does Memory Update?")
    print("="*100)
    
    # Same memory directory
    memory = ClaudeOfficialMemory("./demo_memories_1")
    
    messages = [
        {
            "role": "user",
            "content": """Actually, I wanted to update you on a few things:

1. I just got funding for my startup! We raised $2M seed round.
2. I moved from San Francisco to New York last month.  
3. I've been learning Rust lately and really loving it - might be my new favorite language.
4. Oh, and I hate semicolons now. I prefer languages that don't need them.

Can you help me plan a celebration dinner for the funding? Something nice in NYC."""
        }
    ]
    
    run_conversation_with_memory(messages, memory)


def demo_4_memory_organization():
    """Demo 4: Look at how Claude organized the memories"""
    print("\n" + "="*100) 
    print("🎬 DEMO 4: Memory Organization - How Did Claude Structure Everything?")
    print("="*100)
    
    memory = ClaudeOfficialMemory("./demo_memories_1")
    
    # Let's see what files Claude created
    memory_view = memory.handle_tool_call({"command": "view", "path": "/memories"})
    print("📂 Memory directory structure:")
    print(memory_view)
    
    # Read each file to see how Claude organized information
    import os
    from pathlib import Path
    
    memory_path = Path("./demo_memories_1")
    if memory_path.exists():
        for file_path in memory_path.glob("*"):
            if file_path.is_file():
                print(f"\n📄 Contents of {file_path.name}:")
                print("-" * 60)
                content = memory.handle_tool_call({
                    "command": "view", 
                    "path": f"/memories/{file_path.name}"
                })
                print(content)
                print("-" * 60)


def run_all_demos():
    """Run all memory demos in sequence"""
    
    # Check for API key
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("❌ Please set ANTHROPIC_API_KEY environment variable")
        print("   export ANTHROPIC_API_KEY='your-key-here'")
        return
    
    print("🚀 Starting Live Memory Demonstration with Claude Haiku")
    print("This will show exactly how Claude uses memory in real conversations...")
    
    try:
        demo_1_initial_conversation()
        
        input("\n⏸️ Press Enter to continue to Demo 2 (Memory Recall)...")
        demo_2_memory_recall()
        
        input("\n⏸️ Press Enter to continue to Demo 3 (Memory Evolution)...")
        demo_3_memory_evolution()
        
        input("\n⏸️ Press Enter to continue to Demo 4 (Memory Organization)...")
        demo_4_memory_organization()
        
        print("\n" + "="*100)
        print("✅ DEMO COMPLETE!")
        print("="*100)
        print("Check the ./demo_memories_1/ directory to see the raw memory files Claude created.")
        
    except Exception as e:
        print(f"❌ Error running demo: {e}")
        print("Make sure you have a valid ANTHROPIC_API_KEY set.")


if __name__ == "__main__":
    run_all_demos()