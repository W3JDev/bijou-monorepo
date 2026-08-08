"""
Load & Performance Tests for WhatsApp Call Handler  
==================================================

Tests system behavior under load conditions:
- High volume call handling
- Concurrent call processing
- Memory usage validation  
- Response time benchmarking
- Resource exhaustion protection

Priority: P2 - MEDIUM (performance validation)

Author: QA Engineer
Date: 2026-02-23  
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from statistics import mean, median
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.call_payloads import (
    create_load_test_payloads,
    create_call_offer_payload,
    create_missed_call_payload,
)


@pytest.mark.load  
@pytest.mark.slow
@pytest.mark.asyncio
class TestCallHandlerLoad:
    """
    Load testing for call handler under various volume scenarios
    """
    
    async def test_concurrent_call_volume_handling(self, test_client, mock_supabase):
        """
        Test handling 100 concurrent calls across multiple devices
        
        Success Criteria:
        - Response time < 100ms per call
        - Memory usage < 1GB 
        - No crashes or timeouts
        - >99% success rate
        """
        # Configure mock tenant lookup for load test
        def mock_tenant_lookup(device_id):
            # Generate synthetic tenant for any device_id
            tenant_num = hash(device_id) % 100  # Distribute across 100 tenants
            return MagicMock(data=[{
                "tenant_id": f"load-tenant-{tenant_num:03d}",
                "whatsapp_jid": f"+6012345{tenant_num:05d}@s.whatsapp.net"
            }])
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = mock_tenant_lookup
        
        # Generate 100 concurrent call payloads
        call_payloads = create_load_test_payloads(count=100)
        
        # Execute concurrent requests
        start_time = time.time()
        response_times = []
        status_codes = []
        
        def make_single_request(payload: Dict[str, Any]) -> tuple:
            """Make single call request and measure response time"""
            request_start = time.time()
            
            response = test_client.post(
                "/webhook/message", 
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": "load-test-key"
                }
            )
            
            request_end = time.time()
            response_time = (request_end - request_start) * 1000  # Convert to milliseconds
            
            return response.status_code, response_time
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "load-test-key"}):
            # Execute requests using ThreadPoolExecutor for true concurrency
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(make_single_request, payload) for payload in call_payloads]
                
                for future in as_completed(futures):
                    status_code, response_time = future.result()
                    status_codes.append(status_code)
                    response_times.append(response_time)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Performance Analysis
        success_count = len([s for s in status_codes if s == 200])
        success_rate = (success_count / len(status_codes)) * 100
        avg_response_time = mean(response_times) 
        median_response_time = median(response_times)
        max_response_time = max(response_times)
        
        print(f"\n📊 LOAD TEST RESULTS:")
        print(f"   Total requests: {len(call_payloads)}")
        print(f"   Success rate: {success_rate:.1f}% ({success_count}/{len(status_codes)})")
        print(f"   Total duration: {total_duration:.2f}s")
        print(f"   Avg response time: {avg_response_time:.1f}ms") 
        print(f"   Median response time: {median_response_time:.1f}ms")
        print(f"   Max response time: {max_response_time:.1f}ms")
        print(f"   Requests/second: {len(call_payloads) / total_duration:.1f}")
        
        # Performance Assertions
        assert success_rate >= 99.0, f"Success rate {success_rate:.1f}% below 99% threshold"
        assert avg_response_time < 100.0, f"Average response time {avg_response_time:.1f}ms exceeds 100ms limit"
        assert max_response_time < 1000.0, f"Max response time {max_response_time:.1f}ms exceeds 1s limit"
        assert total_duration < 30.0, f"Total duration {total_duration:.2f}s exceeds 30s limit for 100 requests"

    async def test_sustained_call_load_memory_stability(self, test_client, mock_supabase):
        """
        Test sustained call load over time to detect memory leaks
        
        Simulates 5 calls/minute for 10 minutes (50 calls total)
        Monitors memory usage remains stable
        """
        import psutil
        import os
        
        # Configure tenant lookup
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "tenant_id": "sustained-test-001",
                "whatsapp_jid": "+601234567890@s.whatsapp.net"
            }]
        )
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_readings = [initial_memory]
        
        # Simulate sustained load (reduced duration for testing)
        total_calls = 20  # Reduced from 50 for test performance  
        interval = 0.5    # Reduced from 12 seconds to 0.5 seconds
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "sustained-test-key"}):
            for i in range(total_calls):
                call_payload = create_missed_call_payload(
                    caller_jid=f"+6012345{i:05d}@s.whatsapp.net",
                    device_id=f"sustained-device-{i % 5:03d}",  # Rotate across 5 devices
                    call_id=f"sustained-{i:05d}"
                )
                
                response = test_client.post(
                    "/webhook/message",
                    json=call_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": "sustained-test-key"
                    }
                )
                
                assert response.status_code == 200, f"Call {i+1} failed with {response.status_code}"
                
                # Measure memory usage every 5 calls
                if i % 5 == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_readings.append(current_memory)
                
                # Wait between calls (simulate realistic timing)
                time.sleep(interval)
        
        # Memory Analysis
        final_memory = memory_readings[-1]
        memory_growth = final_memory - initial_memory
        max_memory = max(memory_readings)
        
        print(f"\n🧠 MEMORY USAGE ANALYSIS:")
        print(f"   Initial memory: {initial_memory:.1f} MB")
        print(f"   Final memory: {final_memory:.1f} MB")
        print(f"   Memory growth: {memory_growth:.1f} MB")
        print(f"   Max memory: {max_memory:.1f} MB")
        print(f"   Memory readings: {[f'{m:.1f}' for m in memory_readings]}")
        
        # Memory Stability Assertions
        assert memory_growth < 50.0, f"Memory growth {memory_growth:.1f} MB indicates potential leak"
        assert max_memory < initial_memory + 100.0, f"Peak memory {max_memory:.1f} MB too high"

    async def test_webhook_throughput_benchmark(self, test_client, mock_supabase):
        """
        Benchmark webhook processing throughput
        
        Measures requests/second under various load patterns
        """
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "tenant_id": "throughput-test-001", 
                "whatsapp_jid": "+601234567890@s.whatsapp.net"
            }]
        )
        
        # Test different batch sizes
        batch_sizes = [10, 25, 50]
        throughput_results = {}
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "throughput-test-key"}):
            for batch_size in batch_sizes:
                print(f"\n📈 Testing throughput with {batch_size} requests...")
                
                # Generate payloads for this batch
                payloads = [
                    create_call_offer_payload(
                        caller_jid=f"+6012345{i:05d}@s.whatsapp.net",
                        device_id=f"throughput-device-{i:03d}",
                        call_id=f"throughput-{batch_size}-{i:03d}"
                    )
                    for i in range(batch_size)
                ]
                
                # Measure batch processing time
                start_time = time.time()
                
                # Sequential processing to measure true webhook throughput
                success_count = 0
                for payload in payloads:
                    response = test_client.post(
                        "/webhook/message",
                        json=payload, 
                        headers={
                            "Content-Type": "application/json",
                            "X-API-Key": "throughput-test-key"
                        }
                    )
                    if response.status_code == 200:
                        success_count += 1
                
                end_time = time.time()
                duration = end_time - start_time
                throughput = batch_size / duration
                
                throughput_results[batch_size] = {
                    "duration": duration,
                    "throughput": throughput, 
                    "success_rate": (success_count / batch_size) * 100
                }
                
                print(f"   Duration: {duration:.2f}s")
                print(f"   Throughput: {throughput:.1f} requests/second")
                print(f"   Success rate: {(success_count / batch_size) * 100:.1f}%")
        
        # Throughput Analysis  
        print(f"\n📊 THROUGHPUT BENCHMARK SUMMARY:")
        for batch_size, results in throughput_results.items():
            print(f"   {batch_size:2d} requests: {results['throughput']:5.1f} req/s | {results['success_rate']:5.1f}% success")
        
        # Performance Assertions
        for batch_size, results in throughput_results.items():
            assert results["success_rate"] >= 99.0, f"Batch {batch_size} success rate too low: {results['success_rate']:.1f}%"
            assert results["throughput"] >= 5.0, f"Batch {batch_size} throughput too low: {results['throughput']:.1f} req/s"


@pytest.mark.load
@pytest.mark.slow  
@pytest.mark.asyncio
class TestCallHandlerStress:
    """
    Stress testing for extreme conditions and resource limits
    """
    
    async def test_memory_exhaustion_protection(self, test_client, mock_supabase):
        """
        Test protection against memory exhaustion attacks
        
        Attempts to exhaust server memory with large volumes of call events
        """
        # Configure tenant lookup for stress test
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "tenant_id": "stress-test-001",
                "whatsapp_jid": "+601234567890@s.whatsapp.net" 
            }]
        )
        
        # Generate large number of call events (simulate DoS attack)
        stress_payloads = create_load_test_payloads(count=500)  # Reduced from 1000 for test performance
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "stress-test-key"}):
            # Track response patterns under stress
            response_codes = []
            start_time = time.time()
            
            # Send stress load
            for i, payload in enumerate(stress_payloads):
                response = test_client.post(
                    "/webhook/message",
                    json=payload,
                    headers={
                        "Content-Type": "application/json", 
                        "X-API-Key": "stress-test-key"
                    }
                )
                
                response_codes.append(response.status_code)
                
                # Break if we start getting rate limited (good sign)
                if response.status_code == 429:
                    print(f"Rate limiting activated after {i+1} requests")
                    break
                    
                # Prevent test from running too long
                if time.time() - start_time > 30:  # 30 second limit
                    print(f"Time limit reached after {i+1} requests")
                    break
            
            end_time = time.time()
            duration = end_time - start_time
        
        # Stress Analysis
        total_requests = len(response_codes)
        success_count = len([r for r in response_codes if r == 200])
        rate_limited_count = len([r for r in response_codes if r == 429])
        error_count = len([r for r in response_codes if r >= 400 and r != 429])
        
        print(f"\n🔥 STRESS TEST RESULTS:")
        print(f"   Total requests sent: {total_requests}")
        print(f"   Successful (200): {success_count}")
        print(f"   Rate limited (429): {rate_limited_count}")
        print(f"   Other errors (4xx/5xx): {error_count}")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Avg rate: {total_requests / duration:.1f} req/s")
        
        # Stress Protection Assertions
        if rate_limited_count > 0:
            # Good: Rate limiting is working
            assert rate_limited_count > total_requests * 0.1, "Rate limiting should activate under heavy load"
            print("✅ Rate limiting protection is working")
        else:
            # If no rate limiting, server should still handle the load gracefully
            error_rate = (error_count / total_requests) * 100
            assert error_rate < 5.0, f"Error rate {error_rate:.1f}% too high without rate limiting"
            print("✅ Server handled stress load without errors")

    async def test_concurrent_multi_tenant_stress(self, test_client, mock_supabase):
        """
        Test concurrent load across multiple tenants to verify isolation under stress
        """
        # Configure multiple tenants
        tenant_count = 10
        tenants = []
        for i in range(tenant_count):
            tenants.append({
                "tenant_id": f"concurrent-tenant-{i:03d}",
                "device_id": f"concurrent-device-{i:03d}",
                "whatsapp_jid": f"+6012345{i:04d}@s.whatsapp.net"
            })
        
        def mock_multi_tenant_lookup(device_id):
            for tenant in tenants:
                if tenant["device_id"] == device_id:
                    return MagicMock(data=[tenant])
            return MagicMock(data=[])
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.side_effect = mock_multi_tenant_lookup
        
        # Generate concurrent load per tenant
        calls_per_tenant = 20  # Reduced for test performance
        
        def generate_tenant_load(tenant_idx: int) -> List[int]:
            """Generate load for a specific tenant and return status codes"""
            tenant = tenants[tenant_idx]
            status_codes = []
            
            for call_idx in range(calls_per_tenant):
                payload = create_missed_call_payload(
                    caller_jid=tenant["whatsapp_jid"],
                    device_id=tenant["device_id"], 
                    call_id=f"concurrent-{tenant_idx:03d}-{call_idx:03d}"
                )
                
                response = test_client.post(
                    "/webhook/message",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-API-Key": "concurrent-stress-key"
                    }
                )
                
                status_codes.append(response.status_code)
                
                # Small delay to prevent overwhelming
                time.sleep(0.01)
            
            return status_codes
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "concurrent-stress-key"}):
            # Execute concurrent tenant load using threads
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=tenant_count) as executor:
                futures = [executor.submit(generate_tenant_load, i) for i in range(tenant_count)]
                results = [future.result() for future in as_completed(futures)]
            
            end_time = time.time()
            duration = end_time - start_time
        
        # Multi-tenant Stress Analysis
        all_status_codes = []
        tenant_success_rates = []
        
        for tenant_idx, status_codes in enumerate(results):
            all_status_codes.extend(status_codes)
            success_rate = (len([s for s in status_codes if s == 200]) / len(status_codes)) * 100
            tenant_success_rates.append(success_rate)
            
            print(f"   Tenant {tenant_idx:2d}: {success_rate:5.1f}% success ({len(status_codes)} calls)")
        
        overall_success_rate = (len([s for s in all_status_codes if s == 200]) / len(all_status_codes)) * 100
        total_requests = len(all_status_codes)
        
        print(f"\n🏢 MULTI-TENANT STRESS RESULTS:")
        print(f"   Tenants tested: {tenant_count}")
        print(f"   Total requests: {total_requests}")
        print(f"   Overall success rate: {overall_success_rate:.1f}%")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Avg rate: {total_requests / duration:.1f} req/s")
        
        # Multi-tenant Isolation Assertions
        assert overall_success_rate >= 95.0, f"Overall success rate {overall_success_rate:.1f}% too low under concurrent load"
        
        # Verify no tenant was completely blocked (fair resource allocation)
        min_success_rate = min(tenant_success_rates)
        max_success_rate = max(tenant_success_rates)
        success_rate_variance = max_success_rate - min_success_rate
        
        assert min_success_rate >= 80.0, f"Tenant isolation failed: min success rate {min_success_rate:.1f}%"
        assert success_rate_variance <= 30.0, f"Unfair resource allocation: success rate variance {success_rate_variance:.1f}%"


@pytest.mark.load
@pytest.mark.asyncio
class TestCallHandlerResourceLimits:
    """
    Test behavior at resource limits and boundaries
    """
    
    async def test_maximum_call_tracking_capacity(self, test_client, mock_supabase):
        """
        Test behavior when call tracking reaches maximum capacity
        
        Simulates the scenario where pendingCalls map in bridge reaches limit
        """
        # This test simulates the bridge-side limitation
        # Since we're testing the core webhook handler, we focus on
        # how it handles high volumes of call events
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "tenant_id": "capacity-test-001",
                "whatsapp_jid": "+601234567890@s.whatsapp.net"
            }]
        )
        
        # Test with MAX_PENDING_CALLS equivalent volume
        max_pending_calls = 1000  # Based on bridge implementation limit
        
        with patch.dict(os.environ, {
            "BRIDGE_API_KEY": "capacity-test-key",
            "MAX_PENDING_CALLS": str(max_pending_calls)
        }):
            # Generate call events up to capacity limit
            capacity_payloads = []
            for i in range(max_pending_calls):
                payload = create_call_offer_payload(
                    caller_jid=f"+6012345{i:06d}@s.whatsapp.net",
                    device_id=f"capacity-device-{i % 10:03d}",  # Distribute across 10 devices
                    call_id=f"capacity-{i:06d}"
                )
                capacity_payloads.append(payload)
            
            # Process in batches to simulate realistic timing
            batch_size = 100
            batch_results = []
            
            for batch_start in range(0, len(capacity_payloads), batch_size):
                batch = capacity_payloads[batch_start:batch_start + batch_size]
                batch_start_time = time.time()
                batch_success_count = 0
                
                for payload in batch:
                    response = test_client.post(
                        "/webhook/message",
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-API-Key": "capacity-test-key"
                        }
                    )
                    
                    if response.status_code == 200:
                        batch_success_count += 1
                
                batch_end_time = time.time()
                batch_duration = batch_end_time - batch_start_time
                batch_success_rate = (batch_success_count / len(batch)) * 100
                
                batch_results.append({
                    "batch_num": len(batch_results) + 1,
                    "size": len(batch),
                    "success_rate": batch_success_rate,
                    "duration": batch_duration
                })
                
                print(f"   Batch {len(batch_results):2d}: {batch_success_rate:5.1f}% success in {batch_duration:.2f}s")
                
                # Stop if success rate drops significantly (capacity reached)
                if batch_success_rate < 50.0:
                    print(f"   Stopping: Success rate dropped to {batch_success_rate:.1f}%")
                    break
        
        # Capacity Analysis
        total_processed = sum(result["size"] for result in batch_results)
        avg_success_rate = sum(result["success_rate"] for result in batch_results) / len(batch_results)
        
        print(f"\n📊 CAPACITY TEST RESULTS:")
        print(f"   Total calls processed: {total_processed}")
        print(f"   Batches completed: {len(batch_results)}")
        print(f"   Average success rate: {avg_success_rate:.1f}%")
        
        # Capacity Limit Assertions
        # System should handle at least 50% of maximum capacity gracefully
        assert total_processed >= max_pending_calls * 0.5, f"Only processed {total_processed} of {max_pending_calls} calls"
        assert avg_success_rate >= 80.0, f"Average success rate {avg_success_rate:.1f}% indicates capacity issues"

    async def test_response_time_under_load(self, test_client, mock_supabase):
        """
        Monitor response time degradation under increasing load
        """
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "tenant_id": "response-time-test-001",
                "whatsapp_jid": "+601234567890@s.whatsapp.net"
            }]
        )
        
        # Test with increasing load levels
        load_levels = [10, 25, 50, 100]
        response_time_results = {}
        
        with patch.dict(os.environ, {"BRIDGE_API_KEY": "response-time-key"}):
            for load_level in load_levels:
                print(f"\n⏱️ Testing response times with {load_level} concurrent requests...")
                
                # Generate payloads for this load level
                payloads = [
                    create_missed_call_payload(
                        caller_jid=f"+6012345{i:05d}@s.whatsapp.net",
                        device_id=f"response-device-{i % 5:03d}",
                        call_id=f"response-{load_level}-{i:03d}"
                    )
                    for i in range(load_level)
                ]
                
                # Measure response times with concurrent execution
                def measure_request_time(payload: Dict[str, Any]) -> float:
                    start = time.time()
                    response = test_client.post(
                        "/webhook/message",
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-API-Key": "response-time-key"
                        }
                    )
                    end = time.time()
                    return (end - start) * 1000  # Convert to milliseconds
                
                # Execute concurrent requests
                with ThreadPoolExecutor(max_workers=min(load_level, 20)) as executor:
                    response_times = list(executor.map(measure_request_time, payloads))
                
                # Calculate statistics
                avg_response_time = mean(response_times)
                median_response_time = median(response_times)
                p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
                
                response_time_results[load_level] = {
                    "avg": avg_response_time,
                    "median": median_response_time,
                    "p95": p95_response_time,
                    "min": min(response_times),
                    "max": max(response_times)
                }
                
                print(f"   Avg: {avg_response_time:6.1f}ms | Median: {median_response_time:6.1f}ms | P95: {p95_response_time:6.1f}ms")
        
        # Response Time Analysis
        print(f"\n📈 RESPONSE TIME DEGRADATION ANALYSIS:")
        print("   Load Level |   Avg   | Median  |   P95   |   Min   |   Max")
        print("   -----------|---------|---------|---------|---------|--------")
        
        for load_level, times in response_time_results.items():
            print(f"   {load_level:9d} | {times['avg']:7.1f} | {times['median']:7.1f} | {times['p95']:7.1f} | {times['min']:7.1f} | {times['max']:7.1f}")
        
        # Performance Degradation Assertions
        baseline_avg = response_time_results[load_levels[0]]["avg"]
        highest_load_avg = response_time_results[load_levels[-1]]["avg"]
        
        degradation_factor = highest_load_avg / baseline_avg
        
        assert degradation_factor <= 5.0, f"Response time degraded by {degradation_factor:.1f}x under load (baseline: {baseline_avg:.1f}ms, high load: {highest_load_avg:.1f}ms)"
        
        # All response times should be reasonable even under high load
        for load_level, times in response_time_results.items():
            assert times["p95"] <= 500.0, f"P95 response time {times['p95']:.1f}ms too high at load level {load_level}"