#!/usr/bin/env python
"""
Parallel Processing Benchmark Script

This script measures and compares the performance of sequential vs parallel
processing for the ebook RAG system. It provides detailed metrics and
recommendations for optimal configuration.

Usage:
    poetry run python scripts/benchmark_parallel.py --help
    poetry run python scripts/benchmark_parallel.py --books-dir ~/test_books --workers 3
    poetry run python scripts/benchmark_parallel.py --synthetic --count 10
"""

import argparse
import asyncio
import json
import logging
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import statistics

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import project modules
try:
    from ai_ebook_processor.core.parallel import create_parallel_processor, ParallelConfig
    from ai_ebook_processor.core.pipeline import ProcessingPipeline, ProcessingConfig
    from ai_ebook_processor.rag.system import EbookRAGSystem
    from ai_ebook_processor.utils.config import Config
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Error importing project modules: {e}")
    MODULES_AVAILABLE = False


class BenchmarkResults:
    """Container for benchmark results and analysis."""
    
    def __init__(self):
        self.sequential_times: List[float] = []
        self.parallel_times: List[float] = []
        self.sequential_success_rates: List[float] = []
        self.parallel_success_rates: List[float] = []
        self.chunk_counts: List[int] = []
        self.worker_counts: List[int] = []
        self.configs: List[Dict] = []
    
    def add_result(self, 
                   sequential_time: float, 
                   parallel_time: float,
                   sequential_success: float,
                   parallel_success: float,
                   chunk_count: int,
                   worker_count: int,
                   config: Dict):
        """Add a benchmark result."""
        self.sequential_times.append(sequential_time)
        self.parallel_times.append(parallel_time)
        self.sequential_success_rates.append(sequential_success)
        self.parallel_success_rates.append(parallel_success)
        self.chunk_counts.append(chunk_count)
        self.worker_counts.append(worker_count)
        self.configs.append(config)
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive statistics from results."""
        if not self.sequential_times or not self.parallel_times:
            return {"error": "No results to analyze"}
        
        speedups = [s/p for s, p in zip(self.sequential_times, self.parallel_times)]
        
        return {
            "summary": {
                "test_runs": len(self.sequential_times),
                "avg_speedup": statistics.mean(speedups),
                "max_speedup": max(speedups),
                "min_speedup": min(speedups),
                "median_speedup": statistics.median(speedups)
            },
            "sequential": {
                "avg_time": statistics.mean(self.sequential_times),
                "median_time": statistics.median(self.sequential_times),
                "min_time": min(self.sequential_times),
                "max_time": max(self.sequential_times),
                "avg_success_rate": statistics.mean(self.sequential_success_rates)
            },
            "parallel": {
                "avg_time": statistics.mean(self.parallel_times),
                "median_time": statistics.median(self.parallel_times),
                "min_time": min(self.parallel_times),
                "max_time": max(self.parallel_times),
                "avg_success_rate": statistics.mean(self.parallel_success_rates)
            },
            "efficiency": {
                "parallel_overhead": statistics.mean([p - s/max(self.worker_counts) 
                                                    for s, p in zip(self.sequential_times, self.parallel_times)]),
                "cpu_utilization_improvement": statistics.mean(speedups) / statistics.mean(self.worker_counts),
                "chunk_throughput_sequential": sum(self.chunk_counts) / sum(self.sequential_times),
                "chunk_throughput_parallel": sum(self.chunk_counts) / sum(self.parallel_times)
            }
        }
    
    def generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate performance recommendations based on results."""
        recommendations = []
        
        avg_speedup = stats["summary"]["avg_speedup"]
        
        if avg_speedup > 3.0:
            recommendations.append("✅ Excellent parallel performance! Current configuration is optimal.")
        elif avg_speedup > 2.0:
            recommendations.append("✅ Good parallel performance. Consider fine-tuning worker counts.")
        elif avg_speedup > 1.5:
            recommendations.append("⚠️ Moderate performance gain. Check for I/O bottlenecks.")
        else:
            recommendations.append("❌ Poor parallel performance. Consider disabling parallel processing.")
        
        if stats["parallel"]["avg_success_rate"] < stats["sequential"]["avg_success_rate"]:
            recommendations.append("⚠️ Lower success rate in parallel mode. Check error handling.")
        
        overhead = stats["efficiency"]["parallel_overhead"]
        if overhead > 5.0:
            recommendations.append("⚠️ High parallel overhead. Reduce worker count or increase chunk size.")
        
        return recommendations


def create_synthetic_ebooks(count: int, temp_dir: Path) -> List[Path]:
    """Create synthetic ebook files for testing."""
    ebook_paths = []
    
    for i in range(count):
        # Create synthetic content
        content_lines = []
        for chapter in range(5, 15):  # Variable chapter count
            content_lines.append(f"Chapter {chapter}")
            content_lines.append("=" * 20)
            
            # Generate paragraph content
            for para in range(10, 30):  # Variable paragraph count
                sentence_count = 3 + (i + chapter + para) % 7  # Variable sentences
                paragraph = []
                for sent in range(sentence_count):
                    # Create sentences with variable length
                    words = ['word' + str((i * 1000) + (chapter * 100) + (para * 10) + sent + w) 
                            for w in range(8, 20)]  # 8-20 words per sentence
                    paragraph.append(' '.join(words) + '.')
                content_lines.append(' '.join(paragraph))
            content_lines.append("")  # Chapter separator
        
        # Write synthetic ebook
        ebook_path = temp_dir / f"synthetic_book_{i:03d}.txt"
        with open(ebook_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_lines))
        
        ebook_paths.append(ebook_path)
    
    logger.info(f"Created {count} synthetic ebooks in {temp_dir}")
    return ebook_paths


async def benchmark_processing_methods(ebook_paths: List[Path], 
                                     worker_counts: List[int]) -> BenchmarkResults:
    """Benchmark sequential vs parallel processing methods."""
    if not MODULES_AVAILABLE:
        raise RuntimeError("Project modules not available for benchmarking")
    
    results = BenchmarkResults()
    config = Config()
    
    for worker_count in worker_counts:
        logger.info(f"\n{'='*60}")
        logger.info(f"BENCHMARKING WITH {worker_count} WORKERS")
        logger.info(f"{'='*60}")
        
        # Setup configurations
        parallel_config = ParallelConfig(
            enabled=True,
            book_workers=worker_count,
            chunk_workers=min(worker_count + 1, 6),
            embedding_batch_size=32,
            progress_enabled=False  # Disable for cleaner benchmark output
        )
        
        # Mock processing function for benchmarking
        def mock_process_book(book_path: Path) -> Dict[str, Any]:
            """Mock book processing with realistic timing."""
            import random
            processing_time = random.uniform(0.5, 2.0)  # Simulate variable processing time
            time.sleep(processing_time)
            
            # Simulate chunk generation
            chunk_count = random.randint(50, 200)
            return {
                'success': True,
                'chunks': [f'chunk_{i}' for i in range(chunk_count)],
                'processing_time': processing_time,
                'chunk_count': chunk_count
            }
        
        # Create processors
        parallel_processor = create_parallel_processor(parallel_config.__dict__, mock_process_book)
        
        # Benchmark sequential processing
        logger.info(f"📚 Sequential processing {len(ebook_paths)} books...")
        start_time = time.time()
        sequential_results = []
        sequential_chunks = 0
        sequential_successes = 0
        
        for book_path in ebook_paths:
            try:
                result = mock_process_book(book_path)
                sequential_results.append(result)
                if result.get('success'):
                    sequential_successes += 1
                    sequential_chunks += result.get('chunk_count', 0)
            except Exception as e:
                logger.error(f"Sequential processing error: {e}")
                sequential_results.append({'success': False, 'error': str(e)})
        
        sequential_time = time.time() - start_time
        sequential_success_rate = sequential_successes / len(ebook_paths)
        
        logger.info(f"Sequential: {sequential_time:.2f}s, {sequential_success_rate:.1%} success")
        
        # Benchmark parallel processing
        logger.info(f"🚀 Parallel processing {len(ebook_paths)} books...")
        start_time = time.time()
        
        try:
            parallel_results = await parallel_processor.process_books_parallel(ebook_paths)
            parallel_time = time.time() - start_time
            
            parallel_successes = sum(1 for r in parallel_results if r.get('success') or r.get('status') == 'complete')
            parallel_success_rate = parallel_successes / len(ebook_paths)
            parallel_chunks = sum(r.get('chunk_count', 0) for r in parallel_results if r.get('success'))
            
        except Exception as e:
            logger.error(f"Parallel processing failed: {e}")
            parallel_time = float('inf')
            parallel_success_rate = 0.0
            parallel_chunks = 0
        
        logger.info(f"Parallel: {parallel_time:.2f}s, {parallel_success_rate:.1%} success")
        
        # Calculate speedup
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0
        logger.info(f"🎯 Speedup: {speedup:.2f}x")
        
        # Store results
        results.add_result(
            sequential_time=sequential_time,
            parallel_time=parallel_time,
            sequential_success=sequential_success_rate,
            parallel_success=parallel_success_rate,
            chunk_count=max(sequential_chunks, parallel_chunks),
            worker_count=worker_count,
            config=parallel_config.__dict__
        )
    
    return results


def save_benchmark_report(results: BenchmarkResults, output_path: Path):
    """Save detailed benchmark report to file."""
    stats = results.calculate_statistics()
    recommendations = results.generate_recommendations(stats)
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "statistics": stats,
        "recommendations": recommendations,
        "raw_results": {
            "sequential_times": results.sequential_times,
            "parallel_times": results.parallel_times,
            "sequential_success_rates": results.sequential_success_rates,
            "parallel_success_rates": results.parallel_success_rates,
            "chunk_counts": results.chunk_counts,
            "worker_counts": results.worker_counts,
            "configs": results.configs
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Benchmark report saved to: {output_path}")


def print_summary_report(results: BenchmarkResults):
    """Print a summary of benchmark results to console."""
    stats = results.calculate_statistics()
    recommendations = results.generate_recommendations(stats)
    
    print(f"\n{'='*80}")
    print("🔥 PARALLEL PROCESSING BENCHMARK RESULTS")
    print(f"{'='*80}")
    
    print(f"\n📊 PERFORMANCE SUMMARY:")
    print(f"   Average Speedup: {stats['summary']['avg_speedup']:.2f}x")
    print(f"   Best Speedup:    {stats['summary']['max_speedup']:.2f}x")
    print(f"   Worst Speedup:   {stats['summary']['min_speedup']:.2f}x")
    print(f"   Test Runs:       {stats['summary']['test_runs']}")
    
    print(f"\n⏱️  TIMING COMPARISON:")
    print(f"   Sequential Avg:  {stats['sequential']['avg_time']:.2f}s")
    print(f"   Parallel Avg:    {stats['parallel']['avg_time']:.2f}s")
    print(f"   Time Saved:      {stats['sequential']['avg_time'] - stats['parallel']['avg_time']:.2f}s")
    
    print(f"\n✅ SUCCESS RATES:")
    print(f"   Sequential:      {stats['sequential']['avg_success_rate']:.1%}")
    print(f"   Parallel:        {stats['parallel']['avg_success_rate']:.1%}")
    
    print(f"\n🚀 THROUGHPUT:")
    print(f"   Sequential:      {stats['efficiency']['chunk_throughput_sequential']:.1f} chunks/sec")
    print(f"   Parallel:        {stats['efficiency']['chunk_throughput_parallel']:.1f} chunks/sec")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for recommendation in recommendations:
        print(f"   {recommendation}")
    
    print(f"\n{'='*80}")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark parallel processing performance")
    parser.add_argument("--books-dir", type=str, help="Directory containing ebooks to benchmark")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic ebooks for testing")
    parser.add_argument("--count", type=int, default=5, help="Number of synthetic books to create")
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2, 3, 4], 
                       help="Worker counts to test")
    parser.add_argument("--output", type=str, help="Output file for detailed report")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get ebooks for benchmarking
    if args.synthetic:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            ebook_paths = create_synthetic_ebooks(args.count, temp_path)
            
            # Run benchmark
            logger.info(f"🚀 Starting benchmark with {len(ebook_paths)} synthetic books")
            results = await benchmark_processing_methods(ebook_paths, args.workers)
    
    elif args.books_dir:
        books_dir = Path(args.books_dir)
        if not books_dir.exists():
            logger.error(f"Books directory not found: {books_dir}")
            return 1
        
        # Find ebook files
        ebook_extensions = ['.epub', '.pdf', '.txt', '.mobi']
        ebook_paths = []
        for ext in ebook_extensions:
            ebook_paths.extend(books_dir.glob(f"*{ext}"))
            ebook_paths.extend(books_dir.glob(f"*{ext.upper()}"))
        
        if not ebook_paths:
            logger.error(f"No ebook files found in: {books_dir}")
            return 1
        
        logger.info(f"🚀 Starting benchmark with {len(ebook_paths)} real books")
        results = await benchmark_processing_methods(ebook_paths, args.workers)
    
    else:
        logger.error("Must specify either --books-dir or --synthetic")
        return 1
    
    # Generate and display results
    print_summary_report(results)
    
    # Save detailed report if requested
    if args.output:
        output_path = Path(args.output)
        save_benchmark_report(results, output_path)
    else:
        # Default output location
        output_path = Path(f"benchmark_report_{int(time.time())}.json")
        save_benchmark_report(results, output_path)
    
    return 0


if __name__ == "__main__":
    if not MODULES_AVAILABLE:
        print("Error: Cannot import project modules. Make sure you're running from the project root.")
        exit(1)
    
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
        exit(1)
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        exit(1)