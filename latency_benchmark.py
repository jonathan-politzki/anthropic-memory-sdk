"""
Latency Benchmarking Framework for Memory Systems

This module provides comprehensive latency tracking and analysis for memory operations.
Every memory architecture we build will be measured against these benchmarks.

Key metrics:
- Operation latency (ms)
- Memory size impact
- Success rates
- Percentile distributions (p50, p95, p99)
"""

import time
import json
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import statistics


class OperationType(Enum):
    """Types of memory operations to track"""
    VIEW_DIR = "view_directory"
    VIEW_FILE = "view_file"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SEARCH = "search"
    BATCH_READ = "batch_read"
    REORGANIZE = "reorganize"


@dataclass
class LatencyMetric:
    """Single latency measurement"""
    operation: OperationType
    duration_ms: float
    memory_size_bytes: int
    success: bool
    timestamp: float
    metadata: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'operation': self.operation.value,
            'duration_ms': self.duration_ms,
            'memory_size_bytes': self.memory_size_bytes,
            'success': self.success,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }


class LatencyTracker:
    """
    Core latency tracking system.
    
    Usage:
        tracker = LatencyTracker()
        
        @tracker.track(OperationType.VIEW_FILE)
        def read_memory(path):
            # Your memory read operation
            return data
    """
    
    # Latency thresholds (ms)
    THRESHOLDS = {
        'excellent': 10,
        'good': 50,
        'acceptable': 100,
        'poor': 500
    }
    
    def __init__(self, memory_path: str = "./memories"):
        self.memory_path = Path(memory_path)
        self.metrics: List[LatencyMetric] = []
        self.session_start = time.time()
    
    def track(self, operation: OperationType, **metadata):
        """
        Decorator for tracking operation latency.
        
        Args:
            operation: Type of operation being tracked
            **metadata: Additional metadata to store with the metric
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                exception = None
                result = None
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                except Exception as e:
                    exception = e
                    success = False
                
                duration_ms = (time.perf_counter() - start) * 1000
                
                # Add function arguments to metadata
                meta = {
                    'function': func.__name__,
                    'args': str(args)[:100] if args else '',
                    **metadata
                }
                
                metric = LatencyMetric(
                    operation=operation,
                    duration_ms=duration_ms,
                    memory_size_bytes=self._get_memory_size(),
                    success=success,
                    timestamp=time.time(),
                    metadata=meta
                )
                
                self.metrics.append(metric)
                self._check_latency_threshold(metric)
                
                if exception:
                    raise exception
                return result
            
            return wrapper
        return decorator
    
    def track_manual(self, operation: OperationType, duration_ms: float, 
                    success: bool = True, **metadata):
        """
        Manually track a metric (useful for external operations).
        
        Args:
            operation: Type of operation
            duration_ms: Duration in milliseconds
            success: Whether operation succeeded
            **metadata: Additional metadata
        """
        metric = LatencyMetric(
            operation=operation,
            duration_ms=duration_ms,
            memory_size_bytes=self._get_memory_size(),
            success=success,
            timestamp=time.time(),
            metadata=metadata
        )
        
        self.metrics.append(metric)
        self._check_latency_threshold(metric)
    
    def _get_memory_size(self) -> int:
        """Calculate total memory size in bytes"""
        if not self.memory_path.exists():
            return 0
        
        total_size = 0
        for path in self.memory_path.rglob('*'):
            if path.is_file():
                total_size += path.stat().st_size
        
        return total_size
    
    def _check_latency_threshold(self, metric: LatencyMetric):
        """Alert if latency exceeds thresholds"""
        duration = metric.duration_ms
        op = metric.operation.value
        
        if duration > self.THRESHOLDS['poor']:
            print(f"🔴 CRITICAL: {op} took {duration:.2f}ms")
        elif duration > self.THRESHOLDS['acceptable']:
            print(f"🟠 WARNING: {op} took {duration:.2f}ms")
        elif duration > self.THRESHOLDS['good']:
            print(f"🟡 SLOW: {op} took {duration:.2f}ms")
        # Excellent latency - no alert needed
    
    def get_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile value"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100))
        
        if index >= len(sorted_values):
            return sorted_values[-1]
        
        return sorted_values[index]
    
    def report(self) -> Dict:
        """Generate comprehensive latency report"""
        if not self.metrics:
            return {'error': 'No metrics collected'}
        
        # Group metrics by operation
        by_operation = {}
        for op in OperationType:
            op_metrics = [m for m in self.metrics if m.operation == op]
            if op_metrics:
                latencies = [m.duration_ms for m in op_metrics]
                success_rate = sum(1 for m in op_metrics if m.success) / len(op_metrics)
                
                by_operation[op.value] = {
                    'count': len(op_metrics),
                    'success_rate': round(success_rate, 3),
                    'latency_ms': {
                        'mean': round(statistics.mean(latencies), 2),
                        'median': round(statistics.median(latencies), 2),
                        'stdev': round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
                        'min': round(min(latencies), 2),
                        'max': round(max(latencies), 2),
                        'p50': round(self.get_percentile(latencies, 50), 2),
                        'p95': round(self.get_percentile(latencies, 95), 2),
                        'p99': round(self.get_percentile(latencies, 99), 2)
                    }
                }
        
        # Overall statistics
        all_latencies = [m.duration_ms for m in self.metrics]
        
        # Categorize by performance
        performance_breakdown = {
            'excellent': sum(1 for l in all_latencies if l <= self.THRESHOLDS['excellent']),
            'good': sum(1 for l in all_latencies if self.THRESHOLDS['excellent'] < l <= self.THRESHOLDS['good']),
            'acceptable': sum(1 for l in all_latencies if self.THRESHOLDS['good'] < l <= self.THRESHOLDS['acceptable']),
            'poor': sum(1 for l in all_latencies if l > self.THRESHOLDS['acceptable'])
        }
        
        return {
            'summary': {
                'total_operations': len(self.metrics),
                'session_duration_seconds': round(time.time() - self.session_start, 2),
                'success_rate': round(sum(1 for m in self.metrics if m.success) / len(self.metrics), 3),
                'memory_size_bytes': self._get_memory_size(),
                'memory_size_mb': round(self._get_memory_size() / (1024 * 1024), 2)
            },
            'overall_latency_ms': {
                'mean': round(statistics.mean(all_latencies), 2),
                'median': round(statistics.median(all_latencies), 2),
                'stdev': round(statistics.stdev(all_latencies), 2) if len(all_latencies) > 1 else 0,
                'min': round(min(all_latencies), 2),
                'max': round(max(all_latencies), 2),
                'p50': round(self.get_percentile(all_latencies, 50), 2),
                'p95': round(self.get_percentile(all_latencies, 95), 2),
                'p99': round(self.get_percentile(all_latencies, 99), 2)
            },
            'performance_breakdown': performance_breakdown,
            'by_operation': by_operation,
            'high_latency_operations': [
                {
                    'operation': m.operation.value,
                    'duration_ms': round(m.duration_ms, 2),
                    'timestamp': m.timestamp,
                    'metadata': m.metadata
                }
                for m in sorted(self.metrics, key=lambda x: x.duration_ms, reverse=True)[:10]
                if m.duration_ms > self.THRESHOLDS['acceptable']
            ]
        }
    
    def save_report(self, filepath: str = None):
        """Save report to JSON file"""
        if filepath is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filepath = f"latency_report_{timestamp}.json"
        
        report = self.report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"📊 Latency report saved to {filepath}")
        return filepath
    
    def print_summary(self):
        """Print a human-readable summary"""
        report = self.report()
        
        print("\n" + "="*60)
        print("📊 LATENCY BENCHMARK SUMMARY")
        print("="*60)
        
        summary = report['summary']
        print(f"\n📈 Overall Statistics:")
        print(f"  • Total operations: {summary['total_operations']}")
        print(f"  • Success rate: {summary['success_rate']*100:.1f}%")
        print(f"  • Memory size: {summary['memory_size_mb']:.2f} MB")
        print(f"  • Session duration: {summary['session_duration_seconds']:.1f}s")
        
        latency = report['overall_latency_ms']
        print(f"\n⏱️  Latency Distribution:")
        print(f"  • Mean: {latency['mean']}ms")
        print(f"  • Median (p50): {latency['median']}ms")
        print(f"  • 95th percentile: {latency['p95']}ms")
        print(f"  • 99th percentile: {latency['p99']}ms")
        print(f"  • Min/Max: {latency['min']}ms / {latency['max']}ms")
        
        perf = report['performance_breakdown']
        total = sum(perf.values())
        print(f"\n🎯 Performance Breakdown:")
        print(f"  • Excellent (<{self.THRESHOLDS['excellent']}ms): {perf['excellent']} ({perf['excellent']/total*100:.1f}%)")
        print(f"  • Good (<{self.THRESHOLDS['good']}ms): {perf['good']} ({perf['good']/total*100:.1f}%)")
        print(f"  • Acceptable (<{self.THRESHOLDS['acceptable']}ms): {perf['acceptable']} ({perf['acceptable']/total*100:.1f}%)")
        print(f"  • Poor (>{self.THRESHOLDS['acceptable']}ms): {perf['poor']} ({perf['poor']/total*100:.1f}%)")
        
        if report.get('high_latency_operations'):
            print(f"\n⚠️  Slowest Operations:")
            for op in report['high_latency_operations'][:5]:
                print(f"  • {op['operation']}: {op['duration_ms']}ms")
        
        print("="*60 + "\n")
    
    def export_metrics(self, filepath: str = None) -> str:
        """Export raw metrics to JSON"""
        if filepath is None:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filepath = f"metrics_{timestamp}.json"
        
        metrics_data = [m.to_dict() for m in self.metrics]
        
        with open(filepath, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        return filepath


class LatencyComparator:
    """Compare latency between different memory implementations"""
    
    def __init__(self):
        self.implementations: Dict[str, LatencyTracker] = {}
    
    def add_implementation(self, name: str, tracker: LatencyTracker):
        """Add an implementation's tracker for comparison"""
        self.implementations[name] = tracker
    
    def compare(self) -> Dict:
        """Generate comparison report"""
        if len(self.implementations) < 2:
            return {'error': 'Need at least 2 implementations to compare'}
        
        comparison = {
            'implementations': {},
            'winner_by_metric': {}
        }
        
        # Collect metrics for each implementation
        for name, tracker in self.implementations.items():
            report = tracker.report()
            if 'error' not in report:
                comparison['implementations'][name] = {
                    'mean_latency_ms': report['overall_latency_ms']['mean'],
                    'p95_latency_ms': report['overall_latency_ms']['p95'],
                    'success_rate': report['summary']['success_rate'],
                    'total_operations': report['summary']['total_operations']
                }
        
        # Determine winners for each metric
        metrics_to_compare = ['mean_latency_ms', 'p95_latency_ms', 'success_rate']
        for metric in metrics_to_compare:
            values = {
                name: data[metric] 
                for name, data in comparison['implementations'].items()
            }
            
            if metric == 'success_rate':
                # Higher is better for success rate
                winner = max(values, key=values.get)
            else:
                # Lower is better for latency
                winner = min(values, key=values.get)
            
            comparison['winner_by_metric'][metric] = {
                'winner': winner,
                'value': values[winner]
            }
        
        return comparison
    
    def print_comparison(self):
        """Print comparison results"""
        comparison = self.compare()
        
        if 'error' in comparison:
            print(f"❌ {comparison['error']}")
            return
        
        print("\n" + "="*60)
        print("🏆 IMPLEMENTATION COMPARISON")
        print("="*60)
        
        # Print metrics for each implementation
        for name, metrics in comparison['implementations'].items():
            print(f"\n📦 {name}:")
            print(f"  • Mean latency: {metrics['mean_latency_ms']}ms")
            print(f"  • P95 latency: {metrics['p95_latency_ms']}ms")
            print(f"  • Success rate: {metrics['success_rate']*100:.1f}%")
        
        # Print winners
        print("\n🥇 Winners by Metric:")
        for metric, result in comparison['winner_by_metric'].items():
            print(f"  • {metric}: {result['winner']} ({result['value']})")
        
        print("="*60 + "\n")


# Example usage for testing
if __name__ == "__main__":
    # Create tracker
    tracker = LatencyTracker()
    
    # Simulate some operations
    @tracker.track(OperationType.VIEW_FILE)
    def read_file(path: str) -> str:
        time.sleep(0.02)  # Simulate 20ms read
        return f"Content of {path}"
    
    @tracker.track(OperationType.CREATE)
    def create_file(path: str, content: str) -> bool:
        time.sleep(0.05)  # Simulate 50ms write
        return True
    
    # Run some operations
    for i in range(10):
        read_file(f"file_{i}.txt")
        if i % 3 == 0:
            create_file(f"new_file_{i}.txt", "content")
    
    # Print summary
    tracker.print_summary()
    
    # Save report
    tracker.save_report()