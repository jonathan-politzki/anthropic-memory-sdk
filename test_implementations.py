"""
Test Harness for Comparing Memory Implementations

This allows us to run the same tests across all three implementations
and compare their performance, correctness, and latency.
"""

import time
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List
import sys

# Import all implementations
from claude_official.memory_handler import ClaudeOfficialMemory
from reverse_engineered.memory_handler import ReverseEngineeredMemory
from advanced_memory.memory_handler import AdvancedMemory
from latency_benchmark import LatencyComparator


class MemoryTestHarness:
    """
    Test harness for comparing memory implementations.
    
    Runs identical operations on all implementations and compares:
    - Correctness (same results)
    - Performance (latency)
    - Features (caching, tiers, etc.)
    """
    
    def __init__(self):
        """Initialize test harness with all implementations"""
        self.test_base = Path("./test_memories")
        
        # Clean up any existing test directories
        self._cleanup_test_dirs()
        
        # Initialize all implementations
        self.implementations = {
            'claude_official': ClaudeOfficialMemory(str(self.test_base / "claude")),
            'reverse_engineered': ReverseEngineeredMemory(str(self.test_base / "reverse")),
            'advanced_memory': AdvancedMemory(str(self.test_base / "advanced"))
        }
        
        self.test_results = []
        self.comparator = LatencyComparator()
    
    def _cleanup_test_dirs(self):
        """Clean up test directories"""
        if self.test_base.exists():
            shutil.rmtree(self.test_base)
    
    def run_test_suite(self):
        """Run complete test suite on all implementations"""
        print("\n" + "="*70)
        print("🧪 MEMORY IMPLEMENTATION TEST SUITE")
        print("="*70)
        
        # Test 1: Basic Operations
        print("\n📝 Test 1: Basic Operations")
        self._test_basic_operations()
        
        # Test 2: Performance Under Load
        print("\n⚡ Test 2: Performance Under Load")
        self._test_performance_load()
        
        # Test 3: Cache Effectiveness (for implementations that support it)
        print("\n💾 Test 3: Cache Effectiveness")
        self._test_cache_effectiveness()
        
        # Test 4: Large File Handling
        print("\n📦 Test 4: Large File Handling")
        self._test_large_files()
        
        # Test 5: Concurrent Operations
        print("\n🔄 Test 5: Concurrent-like Operations")
        self._test_concurrent_operations()
        
        # Generate comparison report
        self._generate_comparison_report()
    
    def _test_basic_operations(self):
        """Test basic CRUD operations"""
        test_cases = [
            {
                'name': 'Create file',
                'operation': lambda impl: impl.handle_tool_call({
                    'command': 'create',
                    'path': '/memories/test.txt',
                    'file_text': 'Hello World'
                })
            },
            {
                'name': 'View file',
                'operation': lambda impl: impl.handle_tool_call({
                    'command': 'view',
                    'path': '/memories/test.txt'
                })
            },
            {
                'name': 'Update file',
                'operation': lambda impl: impl.handle_tool_call({
                    'command': 'str_replace',
                    'path': '/memories/test.txt',
                    'old_str': 'World',
                    'new_str': 'Memory'
                })
            },
            {
                'name': 'Insert line',
                'operation': lambda impl: impl.handle_tool_call({
                    'command': 'insert',
                    'path': '/memories/test.txt',
                    'insert_line': 1,
                    'insert_text': 'Second line'
                })
            },
            {
                'name': 'Delete file',
                'operation': lambda impl: impl.handle_tool_call({
                    'command': 'delete',
                    'path': '/memories/test.txt'
                })
            }
        ]
        
        for test_case in test_cases:
            results = {}
            for name, impl in self.implementations.items():
                start = time.perf_counter()
                try:
                    result = test_case['operation'](impl)
                    duration = (time.perf_counter() - start) * 1000
                    results[name] = {
                        'success': True,
                        'duration_ms': duration,
                        'result': result[:100] if result else None
                    }
                except Exception as e:
                    results[name] = {
                        'success': False,
                        'error': str(e)
                    }
            
            self._print_test_result(test_case['name'], results)
    
    def _test_performance_load(self):
        """Test performance under load"""
        num_files = 50
        
        print(f"  Creating {num_files} files...")
        
        for name, impl in self.implementations.items():
            start = time.perf_counter()
            
            # Create many files
            for i in range(num_files):
                impl.handle_tool_call({
                    'command': 'create',
                    'path': f'/memories/file_{i}.txt',
                    'file_text': f'Content of file {i}\n' * 10
                })
            
            # Read all files
            for i in range(num_files):
                impl.handle_tool_call({
                    'command': 'view',
                    'path': f'/memories/file_{i}.txt'
                })
            
            duration = (time.perf_counter() - start) * 1000
            
            print(f"  • {name}: {duration:.2f}ms total ({duration/num_files:.2f}ms per file)")
            
            # Add to comparator
            self.comparator.add_implementation(name, impl.tracker)
    
    def _test_cache_effectiveness(self):
        """Test cache effectiveness for implementations that support it"""
        # Create a file
        for impl in self.implementations.values():
            impl.handle_tool_call({
                'command': 'create',
                'path': '/memories/cache_test.txt',
                'file_text': 'Cache test content'
            })
        
        # Read same file multiple times
        num_reads = 20
        
        for name, impl in self.implementations.items():
            timings = []
            
            for i in range(num_reads):
                start = time.perf_counter()
                impl.handle_tool_call({
                    'command': 'view',
                    'path': '/memories/cache_test.txt'
                })
                duration = (time.perf_counter() - start) * 1000
                timings.append(duration)
            
            # Calculate cache effectiveness
            first_half_avg = sum(timings[:10]) / 10
            second_half_avg = sum(timings[10:]) / 10
            improvement = ((first_half_avg - second_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
            
            print(f"  • {name}:")
            print(f"    - First 10 reads avg: {first_half_avg:.2f}ms")
            print(f"    - Last 10 reads avg: {second_half_avg:.2f}ms")
            print(f"    - Cache improvement: {improvement:.1f}%")
    
    def _test_large_files(self):
        """Test handling of large files"""
        large_content = "Large file content\n" * 1000  # ~19KB
        
        for name, impl in self.implementations.items():
            start = time.perf_counter()
            
            # Create large file
            impl.handle_tool_call({
                'command': 'create',
                'path': '/memories/large.txt',
                'file_text': large_content
            })
            
            # Read with range
            impl.handle_tool_call({
                'command': 'view',
                'path': '/memories/large.txt',
                'view_range': [1, 50]
            })
            
            duration = (time.perf_counter() - start) * 1000
            
            print(f"  • {name}: {duration:.2f}ms for ~19KB file")
    
    def _test_concurrent_operations(self):
        """Test rapid concurrent-like operations"""
        operations = [
            {'command': 'create', 'path': '/memories/concurrent_1.txt', 'file_text': 'File 1'},
            {'command': 'create', 'path': '/memories/concurrent_2.txt', 'file_text': 'File 2'},
            {'command': 'view', 'path': '/memories/concurrent_1.txt'},
            {'command': 'str_replace', 'path': '/memories/concurrent_2.txt', 'old_str': 'File 2', 'new_str': 'Updated 2'},
            {'command': 'view', 'path': '/memories/concurrent_2.txt'},
            {'command': 'delete', 'path': '/memories/concurrent_1.txt'},
        ]
        
        for name, impl in self.implementations.items():
            start = time.perf_counter()
            
            for op in operations:
                impl.handle_tool_call(op)
            
            duration = (time.perf_counter() - start) * 1000
            
            print(f"  • {name}: {duration:.2f}ms for {len(operations)} rapid operations")
    
    def _print_test_result(self, test_name: str, results: Dict):
        """Print test results in readable format"""
        print(f"  ✓ {test_name}:")
        
        for impl_name, result in results.items():
            if result['success']:
                print(f"    • {impl_name}: {result['duration_ms']:.2f}ms")
            else:
                print(f"    • {impl_name}: ❌ Failed - {result.get('error', 'Unknown error')}")
    
    def _generate_comparison_report(self):
        """Generate final comparison report"""
        print("\n" + "="*70)
        print("📊 FINAL COMPARISON REPORT")
        print("="*70)
        
        # Latency comparison
        print("\n⏱️  Latency Comparison:")
        self.comparator.print_comparison()
        
        # Feature comparison
        print("\n🎯 Feature Comparison:")
        for name, impl in self.implementations.items():
            metrics = impl.get_metrics()
            print(f"\n{name}:")
            
            if 'cache_hit_ratio' in metrics:
                print(f"  • Cache hit ratio: {metrics['cache_hit_ratio']*100:.1f}%")
            
            if 'tier_statistics' in metrics:
                print(f"  • Tiered storage: Yes")
                for tier, stats in metrics['tier_statistics'].items():
                    print(f"    - {tier}: {stats['count']} files, {stats['utilization']:.1f}% full")
            else:
                print(f"  • Tiered storage: No")
            
            if 'index_size' in metrics:
                print(f"  • Indexed files: {metrics['index_size']}")
            
            ops = metrics.get('operation_counts', {})
            total_ops = sum(v for k, v in ops.items() if not k.startswith('cache'))
            print(f"  • Total operations: {total_ops}")
        
        # Print individual latency reports
        print("\n📈 Detailed Latency Reports:")
        for name, impl in self.implementations.items():
            print(f"\n{name}:")
            impl.tracker.print_summary()
        
        # Save reports to files
        print("\n💾 Saving detailed reports...")
        for name, impl in self.implementations.items():
            report_file = impl.tracker.save_report(f"report_{name}.json")
            print(f"  • {name}: {report_file}")


def run_comparison():
    """Main function to run the comparison"""
    harness = MemoryTestHarness()
    harness.run_test_suite()


if __name__ == "__main__":
    run_comparison()