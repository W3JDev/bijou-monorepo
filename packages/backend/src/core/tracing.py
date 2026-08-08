"""
W3J Bijou AI - Tracing System
==============================

Distributed tracing for debugging, monitoring, and optimization.

Features:
- Execution flow visualization
- Token usage tracking per step
- Latency breakdown
- Error tracking
- Performance bottleneck identification
- OpenTelemetry integration

Author: W3J Bijou AI
Version: 2.1.0
"""

import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import contextmanager


class TraceSpan:
    """Represents a single trace span (operation)."""
    
    def __init__(
        self,
        name: str,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.span_id = f"{name}_{int(time.time() * 1000000)}"
        self.name = name
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time = None
        self.duration_ms = None
        self.metadata = metadata or {}
        self.events = []
        self.status = "in_progress"
        self.error = None
    
    def add_event(self, name: str, attributes: Optional[Dict] = None):
        """Add an event to this span."""
        self.events.append({
            'timestamp': time.time(),
            'name': name,
            'attributes': attributes or {},
        })
    
    def set_metadata(self, key: str, value: Any):
        """Set metadata attribute."""
        self.metadata[key] = value
    
    def end(self, status: str = "success", error: Optional[str] = None):
        """End this span."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            'span_id': self.span_id,
            'name': self.name,
            'parent_id': self.parent_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms,
            'status': self.status,
            'error': self.error,
            'metadata': self.metadata,
            'events': self.events,
        }


class Tracer:
    """
    Distributed tracing system for Bijou AI.
    Tracks execution flow through TRACE pipeline.
    """
    
    def __init__(self, service_name: str = "bijou-ai"):
        self.service_name = service_name
        self.traces = []
        self.current_trace = None
        self.active_spans = {}
    
    def start_trace(self, trace_name: str, metadata: Optional[Dict] = None) -> str:
        """
        Start a new trace.
        
        Args:
            trace_name: Name of the trace (e.g., "process_message")
            metadata: Initial metadata
            
        Returns:
            Trace ID
        """
        trace_id = f"trace_{int(time.time() * 1000000)}"
        
        self.current_trace = {
            'trace_id': trace_id,
            'name': trace_name,
            'service': self.service_name,
            'start_time': time.time(),
            'metadata': metadata or {},
            'spans': [],
        }
        
        return trace_id
    
    @contextmanager
    def span(
        self,
        name: str,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Context manager for creating a span.
        
        Usage:
            with tracer.span("ASI_execution"):
                # Your code here
                pass
        """
        span = TraceSpan(name, parent_id, metadata)
        self.active_spans[span.span_id] = span
        
        if self.current_trace:
            self.current_trace['spans'].append(span)
        
        try:
            yield span
            span.end(status="success")
        except Exception as e:
            span.end(status="error", error=str(e))
            raise
        finally:
            if span.span_id in self.active_spans:
                del self.active_spans[span.span_id]
    
    def end_trace(self) -> Dict[str, Any]:
        """
        End current trace and return results.
        
        Returns:
            Complete trace data
        """
        if not self.current_trace:
            return {}
        
        self.current_trace['end_time'] = time.time()
        self.current_trace['total_duration_ms'] = (
            self.current_trace['end_time'] - self.current_trace['start_time']
        ) * 1000
        
        # Convert spans to dict
        self.current_trace['spans'] = [
            span.to_dict() if isinstance(span, TraceSpan) else span
            for span in self.current_trace['spans']
        ]
        
        # Store trace
        self.traces.append(self.current_trace)
        
        trace_data = self.current_trace
        self.current_trace = None
        
        return trace_data
    
    def get_trace_summary(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable trace summary."""
        if not trace_data or 'spans' not in trace_data:
            return {}
        
        spans = trace_data['spans']
        
        # Calculate total tokens
        total_tokens = sum(
            span.get('metadata', {}).get('tokens_used', 0)
            for span in spans
        )
        
        # Calculate total cost
        total_cost = sum(
            span.get('metadata', {}).get('cost_usd', 0.0)
            for span in spans
        )
        
        # Find bottlenecks (slowest spans)
        sorted_spans = sorted(
            spans,
            key=lambda x: x.get('duration_ms', 0),
            reverse=True
        )
        
        # Count errors
        error_count = sum(
            1 for span in spans if span.get('status') == 'error'
        )
        
        return {
            'trace_id': trace_data.get('trace_id'),
            'total_duration_ms': trace_data.get('total_duration_ms', 0),
            'total_tokens': total_tokens,
            'total_cost_usd': total_cost,
            'span_count': len(spans),
            'error_count': error_count,
            'slowest_spans': [
                {
                    'name': span.get('name'),
                    'duration_ms': span.get('duration_ms'),
                }
                for span in sorted_spans[:3]
            ],
            'timeline': self._generate_timeline(spans),
        }
    
    def _generate_timeline(self, spans: List[Dict]) -> List[Dict]:
        """Generate execution timeline."""
        if not spans:
            return []
        
        # Sort by start time
        sorted_spans = sorted(spans, key=lambda x: x.get('start_time', 0))
        
        start_time = sorted_spans[0].get('start_time', 0)
        
        timeline = []
        for span in sorted_spans:
            span_start = span.get('start_time', 0)
            offset_ms = (span_start - start_time) * 1000
            
            timeline.append({
                'name': span.get('name'),
                'offset_ms': offset_ms,
                'duration_ms': span.get('duration_ms', 0),
                'status': span.get('status', 'unknown'),
            })
        
        return timeline
    
    def visualize_trace(self, trace_data: Dict[str, Any]) -> str:
        """
        Generate ASCII visualization of trace timeline.
        
        Returns:
            ASCII art timeline
        """
        if not trace_data or 'spans' not in trace_data:
            return "No trace data available"
        
        summary = self.get_trace_summary(trace_data)
        timeline = summary.get('timeline', [])
        
        if not timeline:
            return "No timeline data"
        
        # Build visualization
        lines = []
        lines.append("=" * 80)
        lines.append(f"TRACE: {trace_data.get('name', 'Unknown')}")
        lines.append(f"Total Duration: {summary['total_duration_ms']:.2f}ms")
        lines.append(f"Tokens Used: {summary['total_tokens']}")
        lines.append(f"Cost: ${summary['total_cost_usd']:.4f}")
        lines.append("=" * 80)
        lines.append("")
        lines.append("Timeline:")
        lines.append("")
        
        max_duration = summary['total_duration_ms']
        bar_width = 60
        
        for item in timeline:
            name = item['name']
            duration = item['duration_ms']
            offset = item['offset_ms']
            status = item['status']
            
            # Calculate bar length
            bar_len = int((duration / max_duration) * bar_width)
            offset_len = int((offset / max_duration) * bar_width)
            
            # Status symbol
            symbol = '█' if status == 'success' else '▓' if status == 'error' else '░'
            
            # Build bar
            bar = ' ' * offset_len + symbol * max(1, bar_len)
            
            # Format line
            line = f"{name:25s} |{bar:<{bar_width}}| {duration:6.2f}ms"
            lines.append(line)
        
        lines.append("")
        lines.append("=" * 80)
        
        return '\n'.join(lines)
    
    def export_trace(self, trace_data: Dict[str, Any], format: str = "json") -> str:
        """
        Export trace in various formats.
        
        Args:
            trace_data: Trace to export
            format: 'json' or 'text'
            
        Returns:
            Formatted trace data
        """
        if format == "json":
            return json.dumps(trace_data, indent=2, default=str)
        elif format == "text":
            return self.visualize_trace(trace_data)
        else:
            return str(trace_data)
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Analyze all traces for performance insights."""
        if not self.traces:
            return {'message': 'No traces available'}
        
        # Average duration
        avg_duration = sum(
            t.get('total_duration_ms', 0) for t in self.traces
        ) / len(self.traces)
        
        # Most common bottleneck
        all_spans = []
        for trace in self.traces:
            all_spans.extend(trace.get('spans', []))
        
        # Group by span name
        span_stats = {}
        for span in all_spans:
            name = span.get('name', 'unknown')
            duration = span.get('duration_ms', 0)
            
            if name not in span_stats:
                span_stats[name] = {'count': 0, 'total_duration': 0}
            
            span_stats[name]['count'] += 1
            span_stats[name]['total_duration'] += duration
        
        # Calculate averages
        for name, stats in span_stats.items():
            stats['avg_duration'] = stats['total_duration'] / stats['count']
        
        # Sort by average duration
        bottlenecks = sorted(
            span_stats.items(),
            key=lambda x: x[1]['avg_duration'],
            reverse=True
        )[:5]
        
        return {
            'total_traces': len(self.traces),
            'avg_duration_ms': avg_duration,
            'top_bottlenecks': [
                {
                    'name': name,
                    'avg_duration_ms': stats['avg_duration'],
                    'count': stats['count'],
                }
                for name, stats in bottlenecks
            ],
        }


# Example usage
if __name__ == "__main__":
    tracer = Tracer("bijou-ai-test")
    
    # Start a trace
    trace_id = tracer.start_trace("test_message_processing", {
        'user_id': 'test_user',
        'message': 'Where is my order?'
    })
    
    # Simulate TRACE pipeline
    with tracer.span("ASI_execution", metadata={'model': 'gemini-1.5-flash'}):
        time.sleep(0.1)  # Simulate work
    
    with tracer.span("CAE_execution", metadata={'model': 'gemini-1.5-flash'}):
        time.sleep(0.05)
    
    with tracer.span("SRP_execution", metadata={'model': 'gemini-1.5-pro', 'tokens_used': 450}):
        time.sleep(0.15)
    
    with tracer.span("ERS_execution", metadata={'model': 'gemini-1.5-pro', 'tokens_used': 300}):
        time.sleep(0.08)
    
    # End trace
    trace_data = tracer.end_trace()
    
    # Visualize
    print(tracer.visualize_trace(trace_data))
    print("\nPerformance Insights:")
    print(json.dumps(tracer.get_performance_insights(), indent=2))
