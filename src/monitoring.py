"""
Monitoring Module

Comprehensive monitoring and observability for the slide generation workflow
using Langfuse for LLM call tracking and agent workflow monitoring.
"""

import functools
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from langfuse.callback import CallbackHandler
from langfuse.client import Langfuse

# Load environment variables
load_dotenv()


class SlideGenerationMonitor:
    """
    Centralized monitoring for slide generation workflows using Langfuse

    Tracks:
    - LLM API calls with token usage and costs
    - Agent workflow execution steps
    - Content generation quality metrics
    - Performance and timing data
    - Error rates and patterns
    """

    def __init__(self):
        """Initialize Langfuse monitoring client and callback handler"""
        self._langfuse = None
        self._callback_handler = None
        self._initialize()

    def _initialize(self):
        """Eagerly initialize the Langfuse client."""
        try:
            self._langfuse = Langfuse()
            self._callback_handler = CallbackHandler()
            print(
                "✅ Langfuse monitoring and callback handler initialized successfully"
            )
        except Exception as e:
            print(f"⚠️  Langfuse monitoring disabled: {e}")
            self._langfuse = None
            self._callback_handler = None

    @property
    def langfuse(self):
        """Public property to access the Langfuse client."""
        return self._langfuse

    def get_callback_handler(self) -> Optional[CallbackHandler]:
        """
        Get the Langfuse callback handler for LangGraph workflow tracing

        Returns:
            CallbackHandler instance for unified tracing, or None if disabled
        """
        return self._callback_handler

    def get_monitored_openai_client(self):
        """
        Get OpenAI client for direct API calls

        Note: For LangGraph workflows, use get_callback_handler() instead

        Returns:
            OpenAI client instance
        """
        from openai import OpenAI

        return OpenAI()

    @contextmanager
    def trace_workflow(self, name: str, topic: str, metadata: Optional[Dict] = None):
        """
        Context manager for tracing entire presentation generation workflows

        Args:
            name: Workflow name (e.g., "slide_generation")
            topic: Presentation topic
            metadata: Additional metadata to track
        """
        if not self.langfuse:
            yield None
            return

        # Create workflow trace
        if metadata is None:
            metadata = {}

        trace = self.langfuse.trace(
            name=name,
            input={"topic": topic, "metadata": metadata},
            metadata={"workflow_type": "slide_generation", "topic": topic, **metadata},
        )

        start_time = time.time()

        try:
            yield trace

            # Mark as successful
            duration = time.time() - start_time
            trace.update(
                output={"status": "success", "duration_seconds": duration},
                metadata={
                    "duration_seconds": duration,
                    "status": "success",
                },
            )

        except Exception as e:
            # Mark as failed with error details
            duration = time.time() - start_time
            trace.update(
                output={
                    "status": "error",
                    "error": str(e),
                    "duration_seconds": duration,
                },
                metadata={
                    "duration_seconds": duration,
                    "status": "error",
                    "error_type": type(e).__name__,
                },
            )
            raise

    @contextmanager
    def trace_agent_step(
        self,
        trace_parent,
        agent_name: str,
        step_input: Dict[str, Any],
        step_metadata: Optional[Dict] = None,
    ):
        """
        Context manager for tracing individual agent execution steps

        Args:
            trace_parent: Parent trace object
            agent_name: Name of the agent (e.g., "layout_analyzer", "content_generator")
            step_input: Input data for this agent step
            step_metadata: Additional metadata for this step
        """
        if not self.langfuse or not trace_parent:
            yield None
            return

        # Create agent step span
        if step_metadata is None:
            step_metadata = {}

        span = trace_parent.span(
            name=agent_name,
            input=step_input,
            metadata={"agent_type": agent_name, **step_metadata},
        )

        start_time = time.time()

        try:
            yield span

            # Mark step as successful
            duration = time.time() - start_time
            span.update(
                output={"status": "success", "duration_seconds": duration},
                metadata={
                    "duration_seconds": duration,
                    "status": "success",
                },
            )

        except Exception as e:
            # Mark step as failed
            duration = time.time() - start_time
            span.update(
                output={
                    "status": "error",
                    "error": str(e),
                    "duration_seconds": duration,
                },
                metadata={
                    "duration_seconds": duration,
                    "status": "error",
                    "error_type": type(e).__name__,
                },
            )
            raise

    def track_llm_generation(
        self,
        span_parent,
        generation_type: str,
        prompt: str,
        response: str,
        model: str,
        tokens_used: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ):
        """
        Track LLM generation calls with detailed metrics

        Args:
            span_parent: Parent span for this generation
            generation_type: Type of generation (e.g., "content", "layout_selection")
            prompt: Input prompt
            response: LLM response
            model: Model used
            tokens_used: Number of tokens used
            metadata: Additional tracking metadata
        """
        if not self.langfuse or not span_parent:
            return None

        if metadata is None:
            metadata = {}

        generation = span_parent.generation(
            name=generation_type,
            model=model,
            input=prompt,
            output=response,
            metadata={
                "generation_type": generation_type,
                "model": model,
                "tokens_used": tokens_used,
                **metadata,
            },
        )

        return generation

    def track_content_quality(
        self,
        span_parent,
        content_data: Dict[str, Any],
        quality_metrics: Dict[str, Union[int, float]],
    ):
        """
        Track content quality metrics

        Args:
            span_parent: Parent span
            content_data: Generated content
            quality_metrics: Quality scores and metrics
        """
        if not self.langfuse or not span_parent:
            return

        span_parent.event(
            name="content_quality_check",
            input=content_data,
            output=quality_metrics,
            metadata={"event_type": "quality_metrics", **quality_metrics},
        )

    def track_slide_creation(
        self,
        span_parent,
        slide_number: int,
        layout_used: str,
        placeholders_filled: List[str],
        success: bool = True,
    ):
        """
        Track individual slide creation events

        Args:
            span_parent: Parent span
            slide_number: Slide number created
            layout_used: Layout name used
            placeholders_filled: List of placeholders successfully filled
            success: Whether slide creation was successful
        """
        if not self.langfuse or not span_parent:
            return

        span_parent.event(
            name="slide_created",
            input={
                "slide_number": slide_number,
                "layout_used": layout_used,
                "placeholders_filled": placeholders_filled,
            },
            output={"success": success},
            metadata={
                "event_type": "slide_creation",
                "slide_number": slide_number,
                "layout_used": layout_used,
                "placeholders_count": len(placeholders_filled),
                "success": success,
            },
        )

    def flush(self):
        """Flush any buffered data to Langfuse"""
        if self.langfuse:
            self.langfuse.flush()


# Global instance of the monitor
slide_monitor = SlideGenerationMonitor()


def monitor_agent_execution(agent_name: str):
    """
    Decorator for monitoring agent execution

    Args:
        agent_name: Name of the agent being monitored

    Usage:
        @monitor_agent_execution("layout_analyzer")
        def analyze_layouts(self, ...):
            # Agent logic here
            pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract monitoring context if available
            trace_context = kwargs.pop("_monitor_trace", None)

            if trace_context:
                with slide_monitor.trace_agent_step(
                    trace_context, agent_name, {"args": args, "kwargs": kwargs}
                ) as span:
                    kwargs["_monitor_span"] = span
                    return func(*args, **kwargs)
            else:
                # No monitoring context, run normally
                return func(*args, **kwargs)

        return wrapper

    return decorator


def track_llm_call(call_type: str):
    """
    Decorator for tracking LLM API calls

    Args:
        call_type: Type of LLM call (e.g., "content_generation", "layout_selection")
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            span_context = kwargs.pop("_monitor_span", None)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Track successful LLM call
                if span_context:
                    slide_monitor.track_llm_generation(
                        span_context,
                        call_type,
                        prompt=str(kwargs.get("prompt", "N/A")),
                        response=str(result),
                        model=kwargs.get("model", "unknown"),
                        metadata={"duration_seconds": duration, "success": True},
                    )

                return result

            except Exception as e:
                duration = time.time() - start_time

                # Track failed LLM call
                if span_context:
                    slide_monitor.track_llm_generation(
                        span_context,
                        call_type,
                        prompt=str(kwargs.get("prompt", "N/A")),
                        response=f"ERROR: {str(e)}",
                        model=kwargs.get("model", "unknown"),
                        metadata={
                            "duration_seconds": duration,
                            "success": False,
                            "error": str(e),
                        },
                    )
                raise

        return wrapper

    return decorator
