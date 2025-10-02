"""
Performance tests for search functionality
"""

import pytest
import time
from unittest.mock import patch, Mock
from app.services.hybrid_search import HybridSearchService

class TestSearchPerformance:
    """Performance tests for search services"""
    
    @pytest.fixture
    def mock_search_services(self):
        """Mock search services for performance testing"""
        with patch('app.services.hybrid_search.VectorSearchService') as mock_vec, \
             patch('app.services.hybrid_search.LexicalSearchService') as mock_lex:
            
            # Setup vector search mock
            mock_vec_instance = Mock()
            mock_vec.return_value = mock_vec_instance
            
            # Setup lexical search mock
            mock_lex_instance = Mock()
            mock_lex.return_value = mock_lex_instance
            
            # Create realistic mock data
            semantic_results = [
                {
                    'chunk_id': f'ch_{i:05d}',
                    'doc_id': f'doc_{i%10:02d}',
                    'method': (i % 8) + 1,
                    'page_from': i + 1,
                    'page_to': i + 2,
                    'hash': f'hash_{i:06d}',
                    'source': f'document_{i%5}.pdf',
                    'score': 0.9 - (i * 0.01)
                }
                for i in range(20)
            ]
            
            lexical_results = [
                {
                    'chunk_id': f'ch_{i:05d}',
                    'doc_id': f'doc_{i%10:02d}',
                    'method': (i % 8) + 1,
                    'page_from': i + 1,
                    'page_to': i + 2,
                    'hash': f'hash_{i:06d}',
                    'source': f'document_{i%5}.pdf',
                    'score': 0.8 - (i * 0.01)
                }
                for i in range(20)
            ]
            
            mock_vec_instance.search.return_value = semantic_results
            mock_lex_instance.search.return_value = lexical_results
            
            yield mock_vec_instance, mock_lex_instance
    
    def test_search_latency_p95_target(self, mock_search_services):
        """Test that search meets p95 ≤ 1.5s latency target"""
        mock_vec, mock_lex = mock_search_services
        search_service = HybridSearchService()
        
        # Run multiple searches to get statistical data
        latencies = []
        num_tests = 10
        
        for i in range(num_tests):
            start_time = time.time()
            search_service.search(f"test query {i}", limit=10)
            latency = time.time() - start_time
            latencies.append(latency)
        
        # Calculate p95 latency
        latencies.sort()
        p95_index = int(0.95 * len(latencies))
        p95_latency = latencies[p95_index]
        
        # Verify p95 latency is within target
        assert p95_latency <= 1.5, f"P95 latency {p95_latency:.3f}s exceeds 1.5s target"
    
    def test_search_latency_p99_target(self, mock_search_services):
        """Test that search meets p99 ≤ 3.0s latency target"""
        mock_vec, mock_lex = mock_search_services
        search_service = HybridSearchService()
        
        # Run multiple searches to get statistical data
        latencies = []
        num_tests = 20
        
        for i in range(num_tests):
            start_time = time.time()
            search_service.search(f"test query {i}", limit=10)
            latency = time.time() - start_time
            latencies.append(latency)
        
        # Calculate p99 latency
        latencies.sort()
        p99_index = int(0.99 * len(latencies))
        p99_latency = latencies[p99_index]
        
        # Verify p99 latency is within target
        assert p99_latency <= 3.0, f"P99 latency {p99_latency:.3f}s exceeds 3.0s target"
    
    def test_search_throughput(self, mock_search_services):
        """Test search throughput under load"""
        mock_vec, mock_lex = mock_search_services
        search_service = HybridSearchService()
        
        # Run searches for a fixed duration
        start_time = time.time()
        duration = 2.0  # 2 seconds
        search_count = 0
        
        while time.time() - start_time < duration:
            search_service.search(f"throughput test {search_count}", limit=10)
            search_count += 1
        
        # Calculate throughput (searches per second)
        actual_duration = time.time() - start_time
        throughput = search_count / actual_duration
        
        # Verify reasonable throughput (at least 1 search per second)
        assert throughput >= 1.0, f"Throughput {throughput:.2f} searches/sec is too low"
    
    def test_search_memory_usage(self, mock_search_services):
        """Test that search doesn't consume excessive memory"""
        import psutil
        import os
        
        mock_vec, mock_lex = mock_search_services
        search_service = HybridSearchService()
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Run multiple searches
        for i in range(100):
            search_service.search(f"memory test {i}", limit=10)
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Verify memory increase is reasonable (less than 10MB)
        max_memory_increase = 10 * 1024 * 1024  # 10MB
        assert memory_increase < max_memory_increase, \
            f"Memory increase {memory_increase / 1024 / 1024:.2f}MB exceeds 10MB limit"
    
    def test_search_concurrent_requests(self, mock_search_services):
        """Test search performance under concurrent requests"""
        import threading
        import queue
        
        mock_vec, mock_lex = mock_search_services
        search_service = HybridSearchService()
        
        # Results queue for collecting results
        results_queue = queue.Queue()
        
        def search_worker(worker_id):
            """Worker function for concurrent searches"""
            try:
                start_time = time.time()
                search_service.search(f"concurrent test {worker_id}", limit=10)
                latency = time.time() - start_time
                results_queue.put(('success', worker_id, latency))
            except Exception as e:
                results_queue.put(('error', worker_id, str(e)))
        
        # Start concurrent searches
        num_threads = 5
        threads = []
        
        for i in range(num_threads):
            thread = threading.Thread(target=search_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Verify all searches succeeded
        success_results = [r for r in results if r[0] == 'success']
        assert len(success_results) == num_threads, f"Only {len(success_results)}/{num_threads} searches succeeded"
        
        # Verify all latencies are reasonable
        latencies = [r[2] for r in success_results]
        max_latency = max(latencies)
        assert max_latency <= 5.0, f"Max concurrent latency {max_latency:.3f}s exceeds 5.0s limit"
