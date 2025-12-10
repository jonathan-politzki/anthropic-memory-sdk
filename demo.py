"""
Demo: Anthropic Memory Tool in Action

This script demonstrates how the Memory Tool enables Claude to:
1. Check its memory before starting a task
2. Store information for future reference
3. Retrieve and use stored memories
4. Update memories as it learns

Run this to see the memory tool in action!
"""

import os
import anthropic
from memory_tool import MemoryToolHandler, create_memory_tool_result


def run_conversation(client: anthropic.Anthropic, memory_handler: MemoryToolHandler, 
                    messages: list, max_turns: int = 10) -> str:
    """
    Run a conversation with Claude, handling memory tool calls.
    
    This is the core agentic loop that:
    1. Sends messages to Claude
    2. Processes any tool calls Claude makes
    3. Returns tool results
    4. Continues until Claude's final response
    
    Args:
        client: The Anthropic client
        memory_handler: The memory tool handler
        messages: The conversation messages
        max_turns: Maximum number of turns to prevent infinite loops
        
    Returns:
        Claude's final text response
    """
    
    for turn in range(max_turns):
        print(f"\n{'='*60}")
        print(f"Turn {turn + 1}")
        print('='*60)
        
        # Make API request with the memory tool
        # Beta features are passed via extra_headers
        response = client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=4096,
            tools=[memory_handler.get_tool_definition()],
            messages=messages,
            extra_headers={"anthropic-beta": "context-management-2025-06-27"},
        )
        
        print(f"Stop reason: {response.stop_reason}")
        
        # Check if Claude is done (no more tool calls)
        if response.stop_reason == "end_turn":
            # Extract and return the final text
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            return final_text
        
        # Process tool uses
        tool_results = []
        assistant_content = []
        
        for block in response.content:
            assistant_content.append(block)
            
            if block.type == "text":
                print(f"\n🤖 Claude: {block.text[:200]}..." if len(block.text) > 200 else f"\n🤖 Claude: {block.text}")
            
            elif block.type == "tool_use":
                print(f"\n🔧 Tool call: {block.name}")
                print(f"   Input: {block.input}")
                
                # Execute the memory operation
                result = memory_handler.handle_tool_call(block.input)
                print(f"   Result: {result[:200]}..." if len(result) > 200 else f"   Result: {result}")
                
                tool_results.append(create_memory_tool_result(block.id, result))
        
        # Add assistant message and tool results to conversation
        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})
    
    return "Max turns reached"


def demo_basic_memory():
    """
    Basic demo: Claude stores and retrieves information.
    """
    print("\n" + "="*70)
    print("DEMO 1: Basic Memory - Storing and Retrieving Information")
    print("="*70)
    
    client = anthropic.Anthropic()
    memory_handler = MemoryToolHandler("./memories")
    
    # First conversation: Ask Claude to remember something
    messages = [
        {
            "role": "user",
            "content": """I want you to remember some important information about my project:
            
Project Name: MemoryAI
Tech Stack: Python, FastAPI, PostgreSQL
Goal: Build an intelligent agent memory system

Please store this in your memory and confirm you've saved it."""
        }
    ]
    
    response = run_conversation(client, memory_handler, messages)
    print(f"\n✅ Final response:\n{response}")


def demo_memory_recall():
    """
    Demo: Claude recalls previously stored information.
    """
    print("\n" + "="*70)
    print("DEMO 2: Memory Recall - Retrieving Stored Information")
    print("="*70)
    
    client = anthropic.Anthropic()
    memory_handler = MemoryToolHandler("./memories")
    
    # Ask Claude to recall the information
    messages = [
        {
            "role": "user",
            "content": "What do you remember about my project? Check your memories."
        }
    ]
    
    response = run_conversation(client, memory_handler, messages)
    print(f"\n✅ Final response:\n{response}")


def demo_learning_from_feedback():
    """
    Demo: Claude learns from feedback and updates memory.
    """
    print("\n" + "="*70)
    print("DEMO 3: Learning from Feedback")
    print("="*70)
    
    client = anthropic.Anthropic()
    memory_handler = MemoryToolHandler("./memories")
    
    messages = [
        {
            "role": "user",
            "content": """I want to give you some feedback about how I like my code formatted:
            
1. I prefer 4-space indentation
2. I like docstrings on all public functions
3. I prefer type hints
4. I like functions to be under 50 lines

Please save these preferences for future reference."""
        }
    ]
    
    response = run_conversation(client, memory_handler, messages)
    print(f"\n✅ Final response:\n{response}")


def demo_complex_task():
    """
    Demo: Claude uses memory to help with a complex task.
    """
    print("\n" + "="*70)
    print("DEMO 4: Complex Task with Memory Context")
    print("="*70)
    
    client = anthropic.Anthropic()
    memory_handler = MemoryToolHandler("./memories")
    
    messages = [
        {
            "role": "user",
            "content": """I need help writing a function. First check your memory 
for any coding preferences I've shared, then write a function that 
calculates the fibonacci sequence up to n numbers.

Make sure to follow any preferences you find in your memory!"""
        }
    ]
    
    response = run_conversation(client, memory_handler, messages)
    print(f"\n✅ Final response:\n{response}")


def demo_interactive():
    """
    Interactive demo: Chat with Claude using memory.
    """
    print("\n" + "="*70)
    print("INTERACTIVE MODE: Chat with Claude (with Memory)")
    print("="*70)
    print("Type 'quit' to exit, 'clear' to clear memories, 'show' to view memories")
    print("="*70)
    
    client = anthropic.Anthropic()
    memory_handler = MemoryToolHandler("./memories")
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if user_input.lower() == 'quit':
                print("Goodbye!")
                break
            elif user_input.lower() == 'clear':
                import shutil
                shutil.rmtree("./memories", ignore_errors=True)
                memory_handler._ensure_directory_exists()
                print("🗑️  Memories cleared!")
                continue
            elif user_input.lower() == 'show':
                result = memory_handler.handle_tool_call({"command": "view", "path": "/memories"})
                print(f"📁 Memories:\n{result}")
                continue
            elif not user_input:
                continue
            
            messages = [{"role": "user", "content": user_input}]
            response = run_conversation(client, memory_handler, messages)
            print(f"\n🤖 Claude: {response}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break


def main():
    """Main entry point."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║              Anthropic Memory Tool Demo                              ║
║                                                                      ║
║  This demo shows how Claude can store and retrieve information       ║
║  across conversations using the Memory Tool.                         ║
║                                                                      ║
║  The future of AI is agentic memory - moving from RAG to            ║
║  intelligent, persistent memory that learns and evolves.             ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("   Please set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return
    
    print("\nSelect a demo:")
    print("1. Basic Memory - Store information")
    print("2. Memory Recall - Retrieve stored information")  
    print("3. Learning from Feedback - Save preferences")
    print("4. Complex Task - Use memory context")
    print("5. Interactive Mode - Chat with memory")
    print("6. Run all demos (1-4)")
    
    choice = input("\nEnter choice (1-6): ").strip()
    
    demos = {
        "1": demo_basic_memory,
        "2": demo_memory_recall,
        "3": demo_learning_from_feedback,
        "4": demo_complex_task,
        "5": demo_interactive,
    }
    
    if choice == "6":
        for i in ["1", "2", "3", "4"]:
            demos[i]()
    elif choice in demos:
        demos[choice]()
    else:
        print("Invalid choice. Running interactive mode by default...")
        demo_interactive()


if __name__ == "__main__":
    main()

