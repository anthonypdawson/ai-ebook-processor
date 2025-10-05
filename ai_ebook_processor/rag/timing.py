"""
Performance timing utilities for the RAG system

This module provides decorators and context managers for measuring and logging
execution time of functions and code blocks to help identify performance bottlenecks.
"""

import time
import logging
from functools import wraps
from typing import Dict, Any

logger = logging.getLogger(__name__)


def timing_decorator(operation_name: str = None):
    """Decorator to measure and log execution time of functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time
                name = operation_name or f"{func.__qualname__}"
                # Log timing info at debug level to avoid spam
                logger.debug(f"⏱️  {name}: {duration:.3f}s")
                # For operations taking longer than 1 second, log at info level
                if duration > 1.0:
                    logger.info(f"🐌 Slow operation - {name}: {duration:.3f}s")
        return wrapper
    return decorator


class Timer:
    """Context manager for timing code blocks"""
    def __init__(self, operation_name: str, verbose: bool = False, threshold: float = 0.5):
        self.operation_name = operation_name
        self.verbose = verbose
        self.threshold = threshold
        self.start_time = None
        self.duration = None
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        if self.verbose:
            print(f"⏱️  Starting: {self.operation_name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.perf_counter()
        self.duration = end_time - self.start_time
        if self.verbose or self.duration > self.threshold:
            print(f"⏱️  {self.operation_name}: {self.duration:.3f}s")
        logger.debug(f"⏱️  {self.operation_name}: {self.duration:.3f}s")


class PerformanceAnalyzer:
    """Analyze and report performance bottlenecks"""
    
    @staticmethod
    def analyze_db_operation(operation_name: str, result_count: int, duration: float) -> Dict[str, Any]:
        """Analyze database operation performance"""
        analysis = {
            'operation': operation_name,
            'duration': duration,
            'result_count': result_count,
            'per_item_ms': (duration * 1000 / result_count) if result_count > 0 else 0,
            'performance_rating': 'unknown'
        }
        
        # Performance thresholds for different operations
        if 'metadata' in operation_name.lower():
            # Metadata queries should be very fast
            if duration < 0.1:
                analysis['performance_rating'] = 'excellent'
            elif duration < 0.5:
                analysis['performance_rating'] = 'good'
            elif duration < 1.0:
                analysis['performance_rating'] = 'fair'
            else:
                analysis['performance_rating'] = 'poor'
        elif 'query' in operation_name.lower():
            # Search queries can be a bit slower
            if duration < 0.2:
                analysis['performance_rating'] = 'excellent'
            elif duration < 0.8:
                analysis['performance_rating'] = 'good'
            elif duration < 2.0:
                analysis['performance_rating'] = 'fair'
            else:
                analysis['performance_rating'] = 'poor'
        
        return analysis
    
    @staticmethod
    def suggest_optimizations(analysis: Dict[str, Any]) -> str:
        """Suggest optimizations based on performance analysis"""
        suggestions = []
        
        if analysis['performance_rating'] == 'poor':
            if analysis['result_count'] > 1000:
                suggestions.append("Consider adding pagination or limiting results")
            if 'metadata' in analysis['operation'].lower():
                suggestions.append("Database may need indexing or the collection is very large")
                suggestions.append("Consider using ChromaDB's include parameter to fetch only needed fields")
            if 'query' in analysis['operation'].lower():
                suggestions.append("Consider reducing n_results or using more specific queries")
        
        elif analysis['performance_rating'] == 'fair':
            suggestions.append("Performance is acceptable but could be optimized")
            if analysis['per_item_ms'] > 10:
                suggestions.append("High per-item processing time - check data structure efficiency")
        
        return "; ".join(suggestions) if suggestions else "Performance is acceptable"


def detailed_timer(operation_name: str, show_analysis: bool = False):
    """Enhanced timer with performance analysis"""
    class DetailedTimer(Timer):
        def __init__(self):
            super().__init__(operation_name, threshold=0.1)
            self.show_analysis = show_analysis
            self.result_count = 0
            
        def set_result_count(self, count: int):
            self.result_count = count
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            super().__exit__(exc_type, exc_val, exc_tb)
            
            if self.show_analysis and self.duration is not None:
                analysis = PerformanceAnalyzer.analyze_db_operation(
                    operation_name, self.result_count, self.duration
                )
                
                print(f"📊 Performance Analysis:")
                print(f"   Duration: {analysis['duration']:.3f}s")
                print(f"   Items: {analysis['result_count']}")
                print(f"   Per-item: {analysis['per_item_ms']:.1f}ms")
                print(f"   Rating: {analysis['performance_rating']}")
                
                suggestions = PerformanceAnalyzer.suggest_optimizations(analysis)
                if suggestions != "Performance is acceptable":
                    print(f"💡 Suggestions: {suggestions}")
    
    return DetailedTimer()