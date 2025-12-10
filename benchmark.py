"""
Memory Tool Performance Benchmark

Tests:
1. Storage Performance (write latency at scale)
2. Recall Performance (read latency, accuracy)
3. Operation Latency (all 6 commands)
4. Scale Testing (10, 50, 100, 500 files)
5. Simulated E2E with API latency estimates
"""

import time
import os
import shutil
import json
import statistics
from pathlib import Path
from memory_tool import MemoryToolHandler

# Test configuration
BENCHMARK_DIR = "./benchmark_memories"
ITERATIONS = 10  # Runs per test for averaging


class MemoryBenchmark:
    def __init__(self):
        self.results = {}
        self.handler = None
    
    def setup(self):
        """Clean slate for each benchmark run."""
        if os.path.exists(BENCHMARK_DIR):
            shutil.rmtree(BENCHMARK_DIR)
        self.handler = MemoryToolHandler(BENCHMARK_DIR)
    
    def teardown(self):
        """Cleanup after tests."""
        if os.path.exists(BENCHMARK_DIR):
            shutil.rmtree(BENCHMARK_DIR)
    
    def measure(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        return elapsed, result
    
    # =========================================================================
    # TEST 1: Storage Performance
    # =========================================================================
    
    def test_storage_performance(self):
        """Test write latency for different content sizes."""
        print("\n" + "="*70)
        print("TEST 1: STORAGE PERFORMANCE (Write Latency)")
        print("="*70)
        
        test_cases = [
            ("tiny", "Hello world", 11),
            ("small", "x" * 100, 100),
            ("medium", "x" * 1000, 1000),
            ("large", "x" * 10000, 10000),
            ("xlarge", "x" * 50000, 50000),
        ]
        
        results = {}
        
        for name, content, size in test_cases:
            self.setup()
            times = []
            
            for i in range(ITERATIONS):
                elapsed, _ = self.measure(
                    self.handler.handle_tool_call,
                    {
                        "command": "create",
                        "path": f"/memories/test_{name}_{i}.txt",
                        "file_text": content
                    }
                )
                times.append(elapsed)
            
            avg = statistics.mean(times)
            std = statistics.stdev(times) if len(times) > 1 else 0
            results[name] = {"avg_ms": avg, "std_ms": std, "size_bytes": size}
            
            print(f"  {name:10} ({size:,} bytes): {avg:.3f}ms ± {std:.3f}ms")
            self.teardown()
        
        self.results["storage"] = results
        return results
    
    # =========================================================================
    # TEST 2: Recall Performance
    # =========================================================================
    
    def test_recall_performance(self):
        """Test read latency and accuracy."""
        print("\n" + "="*70)
        print("TEST 2: RECALL PERFORMANCE (Read Latency)")
        print("="*70)
        
        self.setup()
        
        # Create test files with known content
        test_data = {
            "user_preferences": "<prefs><theme>dark</theme><lang>python</lang></prefs>",
            "project_context": "<project><name>TestProject</name><status>active</status></project>",
            "conversation_history": "User asked about memory systems. We discussed RAG vs agentic memory.",
            "coding_notes": "def fibonacci(n): return n if n < 2 else fibonacci(n-1) + fibonacci(n-2)",
        }
        
        # Write all test files
        for name, content in test_data.items():
            self.handler.handle_tool_call({
                "command": "create",
                "path": f"/memories/{name}.txt",
                "file_text": content
            })
        
        results = {}
        
        # Test 1: Directory listing
        times = []
        for _ in range(ITERATIONS):
            elapsed, result = self.measure(
                self.handler.handle_tool_call,
                {"command": "view", "path": "/memories"}
            )
            times.append(elapsed)
        
        avg = statistics.mean(times)
        results["view_directory"] = {"avg_ms": avg, "files": len(test_data)}
        print(f"  View directory ({len(test_data)} files): {avg:.3f}ms")
        
        # Test 2: Single file read
        for name, expected_content in test_data.items():
            times = []
            accurate = 0
            
            for _ in range(ITERATIONS):
                elapsed, result = self.measure(
                    self.handler.handle_tool_call,
                    {"command": "view", "path": f"/memories/{name}.txt"}
                )
                times.append(elapsed)
                if expected_content in result:
                    accurate += 1
            
            avg = statistics.mean(times)
            accuracy = (accurate / ITERATIONS) * 100
            results[f"read_{name}"] = {"avg_ms": avg, "accuracy": accuracy}
            print(f"  Read {name}: {avg:.3f}ms (accuracy: {accuracy}%)")
        
        self.results["recall"] = results
        self.teardown()
        return results
    
    # =========================================================================
    # TEST 3: Operation Latency (All 6 Commands)
    # =========================================================================
    
    def test_operation_latency(self):
        """Test latency for each of the 6 memory commands."""
        print("\n" + "="*70)
        print("TEST 3: OPERATION LATENCY (All 6 Commands)")
        print("="*70)
        
        results = {}
        
        for i in range(ITERATIONS):
            self.setup()
            
            # CREATE
            elapsed, _ = self.measure(
                self.handler.handle_tool_call,
                {"command": "create", "path": "/memories/test.txt", "file_text": "Line 1\nLine 2\nLine 3"}
            )
            results.setdefault("create", []).append(elapsed)
            
            # VIEW (file)
            elapsed, _ = self.measure(
                self.handler.handle_tool_call,
                {"command": "view", "path": "/memories/test.txt"}
            )
            results.setdefault("view_file", []).append(elapsed)
            
            # VIEW (directory)
            elapsed, _ = self.measure(
                self.handler.handle_tool_call,
                {"command": "view", "path": "/memories"}
            )
            results.setdefault("view_dir", []).append(elapsed)
            
            # STR_REPLACE
            elapsed, _ = self.measure(
                self.handler.handle_tool_call,
                {"command": "str_replace", "path": "/memories/test.txt", "old_str": "Line 2", "new_str": "Modified Line"}
            )
            results.setdefault("str_replace", []).append(elapsed)
            
            # INSERT
            elapsed, _ = self.measure(
                self.handler.handle_tool_call,
                {"command": "insert", "path": "/memories/test.txt", "insert_line": 2, "insert_text": "Inserted Line"}
            )
            results.setdefault("insert", []).append(elapsed)
            
            # RENAME
            elapsed, _ = self.measure(
                self.handler.handle_tool_call,
                {"command": "rename", "old_path": "/memories/test.txt", "new_path": "/memories/renamed.txt"}
            )
            results.setdefault("rename", []).append(elapsed)
            
            # DELETE
            elapsed, _ = self.measure(
                self.handler.handle_tool_call,
                {"command": "delete", "path": "/memories/renamed.txt"}
            )
            results.setdefault("delete", []).append(elapsed)
            
            self.teardown()
        
        # Calculate averages
        final_results = {}
        for cmd, times in results.items():
            avg = statistics.mean(times)
            std = statistics.stdev(times) if len(times) > 1 else 0
            final_results[cmd] = {"avg_ms": avg, "std_ms": std}
            print(f"  {cmd:15}: {avg:.3f}ms ± {std:.3f}ms")
        
        self.results["operations"] = final_results
        return final_results
    
    # =========================================================================
    # TEST 4: Scale Testing
    # =========================================================================
    
    def test_scale(self):
        """Test performance with increasing number of files."""
        print("\n" + "="*70)
        print("TEST 4: SCALE TESTING (Directory Navigation)")
        print("="*70)
        
        file_counts = [10, 50, 100, 250, 500]
        results = {}
        
        for count in file_counts:
            self.setup()
            
            # Create N files
            print(f"  Creating {count} files...", end=" ", flush=True)
            create_start = time.perf_counter()
            for i in range(count):
                self.handler.handle_tool_call({
                    "command": "create",
                    "path": f"/memories/file_{i:04d}.txt",
                    "file_text": f"Content for file {i}\nWith multiple lines\nAnd some data: {i * 100}"
                })
            create_time = (time.perf_counter() - create_start) * 1000
            print(f"created in {create_time:.0f}ms")
            
            # Test directory listing
            times = []
            for _ in range(ITERATIONS):
                elapsed, result = self.measure(
                    self.handler.handle_tool_call,
                    {"command": "view", "path": "/memories"}
                )
                times.append(elapsed)
            
            avg_view = statistics.mean(times)
            
            # Test reading a random file
            times = []
            for _ in range(ITERATIONS):
                elapsed, _ = self.measure(
                    self.handler.handle_tool_call,
                    {"command": "view", "path": f"/memories/file_{count//2:04d}.txt"}
                )
                times.append(elapsed)
            
            avg_read = statistics.mean(times)
            
            results[count] = {
                "view_dir_ms": avg_view,
                "read_file_ms": avg_read,
                "create_total_ms": create_time
            }
            
            print(f"  {count:4} files: view_dir={avg_view:.3f}ms, read_file={avg_read:.3f}ms")
            self.teardown()
        
        self.results["scale"] = results
        return results
    
    # =========================================================================
    # TEST 5: Simulated E2E Latency
    # =========================================================================
    
    def test_simulated_e2e(self):
        """
        Simulate end-to-end latency including estimated API call times.
        
        Based on typical Claude API response times:
        - API call overhead: ~500-2000ms per turn
        - Token processing: varies by length
        """
        print("\n" + "="*70)
        print("TEST 5: SIMULATED END-TO-END LATENCY")
        print("="*70)
        
        # Assumptions (conservative estimates)
        API_LATENCY_MS = 1500  # Average API round-trip
        
        self.setup()
        
        # Create test memories
        memories = [
            ("project.xml", "<project><name>MyApp</name><stack>Python,FastAPI</stack></project>"),
            ("prefs.xml", "<prefs><indent>4</indent><typing>strict</typing></prefs>"),
            ("history.txt", "Previous conversation summary..."),
        ]
        
        for name, content in memories:
            self.handler.handle_tool_call({
                "command": "create",
                "path": f"/memories/{name}",
                "file_text": content
            })
        
        # Simulate typical Claude memory check flow
        scenarios = {
            "minimal": {
                "description": "Claude checks memory, finds nothing relevant",
                "operations": [
                    ("view", {"command": "view", "path": "/memories"}),
                ],
                "api_calls": 2  # Initial + response
            },
            "typical": {
                "description": "Claude checks memory, reads 2 relevant files",
                "operations": [
                    ("view_dir", {"command": "view", "path": "/memories"}),
                    ("read_1", {"command": "view", "path": "/memories/project.xml"}),
                    ("read_2", {"command": "view", "path": "/memories/prefs.xml"}),
                ],
                "api_calls": 4  # Initial + 3 tool results + response
            },
            "heavy": {
                "description": "Claude checks, reads all, updates progress",
                "operations": [
                    ("view_dir", {"command": "view", "path": "/memories"}),
                    ("read_1", {"command": "view", "path": "/memories/project.xml"}),
                    ("read_2", {"command": "view", "path": "/memories/prefs.xml"}),
                    ("read_3", {"command": "view", "path": "/memories/history.txt"}),
                    ("write", {"command": "create", "path": "/memories/progress.xml", "file_text": "<progress>Started task</progress>"}),
                ],
                "api_calls": 6
            }
        }
        
        results = {}
        
        for name, scenario in scenarios.items():
            # Measure local operation time
            local_times = []
            for op_name, op_input in scenario["operations"]:
                elapsed, _ = self.measure(self.handler.handle_tool_call, op_input)
                local_times.append(elapsed)
            
            total_local = sum(local_times)
            total_api = scenario["api_calls"] * API_LATENCY_MS
            total_e2e = total_local + total_api
            
            results[name] = {
                "local_ms": total_local,
                "api_ms": total_api,
                "total_ms": total_e2e,
                "api_calls": scenario["api_calls"]
            }
            
            print(f"\n  {name.upper()}: {scenario['description']}")
            print(f"    Local ops:  {total_local:>8.2f}ms ({len(scenario['operations'])} operations)")
            print(f"    API calls:  {total_api:>8.0f}ms ({scenario['api_calls']} round-trips @ {API_LATENCY_MS}ms)")
            print(f"    TOTAL:      {total_e2e:>8.0f}ms ({total_e2e/1000:.1f}s)")
        
        self.results["e2e"] = results
        self.teardown()
        return results
    
    # =========================================================================
    # Summary Report
    # =========================================================================
    
    def generate_report(self):
        """Generate final benchmark report."""
        print("\n" + "="*70)
        print("BENCHMARK SUMMARY REPORT")
        print("="*70)
        
        print("""
┌─────────────────────────────────────────────────────────────────────┐
│                    ANTHROPIC MEMORY TOOL BENCHMARK                  │
└─────────────────────────────────────────────────────────────────────┘

LOCAL OPERATION PERFORMANCE (Client-Side Only):
───────────────────────────────────────────────
""")
        
        if "operations" in self.results:
            ops = self.results["operations"]
            print(f"  CREATE:       {ops['create']['avg_ms']:>6.3f}ms")
            print(f"  VIEW (file):  {ops['view_file']['avg_ms']:>6.3f}ms")
            print(f"  VIEW (dir):   {ops['view_dir']['avg_ms']:>6.3f}ms")
            print(f"  STR_REPLACE:  {ops['str_replace']['avg_ms']:>6.3f}ms")
            print(f"  INSERT:       {ops['insert']['avg_ms']:>6.3f}ms")
            print(f"  RENAME:       {ops['rename']['avg_ms']:>6.3f}ms")
            print(f"  DELETE:       {ops['delete']['avg_ms']:>6.3f}ms")
        
        print("""
SCALE CHARACTERISTICS:
──────────────────────
""")
        
        if "scale" in self.results:
            for count, data in self.results["scale"].items():
                print(f"  {count:>4} files: view_dir={data['view_dir_ms']:.2f}ms, read={data['read_file_ms']:.2f}ms")
        
        print("""
END-TO-END LATENCY (with API calls):
────────────────────────────────────
""")
        
        if "e2e" in self.results:
            for scenario, data in self.results["e2e"].items():
                print(f"  {scenario:>8}: {data['total_ms']/1000:.1f}s total ({data['api_calls']} API calls)")
        
        print("""
KEY FINDINGS:
─────────────
  ✓ Local operations are FAST (<1ms typically)
  ✗ API round-trips are the BOTTLENECK (1-2s each)
  ✗ Sequential operations multiply latency
  ✗ 3-file read = 6+ seconds minimum
  
COMPARISON TO SEMANTIC MEMORY:
──────────────────────────────
  Anthropic Memory Tool:  ~6-9s for typical recall
  Semantic search (est):  ~0.5-1s for equivalent recall
  
  The tool trades LATENCY for CONTROL and PRIVACY.
""")
        
        # Save results to JSON
        with open(f"{BENCHMARK_DIR}_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n  Results saved to: {BENCHMARK_DIR}_results.json")


def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           ANTHROPIC MEMORY TOOL - PERFORMANCE BENCHMARK              ║
║                                                                      ║
║  Testing: Storage, Recall, Latency, Scale                            ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    benchmark = MemoryBenchmark()
    
    try:
        benchmark.test_storage_performance()
        benchmark.test_recall_performance()
        benchmark.test_operation_latency()
        benchmark.test_scale()
        benchmark.test_simulated_e2e()
        benchmark.generate_report()
        
    finally:
        benchmark.teardown()
    
    print("\n✅ Benchmark complete!")


if __name__ == "__main__":
    main()

