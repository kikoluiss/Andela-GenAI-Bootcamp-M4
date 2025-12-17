import os
import sys
import time
import logging
from contextlib import contextmanager
from typing import Optional, Dict, Any

from httpx import get
from langfuse import get_client

from .config import LANGFUSE_BASE_URL

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Initialize Langfuse client with proper error handling
_langfuse = None
try:
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    
    if public_key and secret_key:
        # Try base_url first (newer SDK versions), fall back to host
        try:
            _langfuse = get_client()
        except Exception as e:
            # Fall back to host parameter for older SDK versions
            logger.error(f"Failed to initialize Langfuse client: {e}")
        logger.info("Langfuse client initialized successfully")
    else:
        logger.warning("Langfuse API keys not found. Tracing will use no-op implementations.")
except Exception as e:
    logger.warning(f"Failed to initialize Langfuse client: {e}. Tracing will use no-op implementations.")


class _NoOpSpan:
    def __init__(self, name: str = None, input: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.input = input
        self.metadata = metadata

    def update(self, *args, **kwargs):
        return None

    def end(self):
        return None


class _NoOpTrace:
    def __init__(self, name: str = None, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.metadata = metadata

    def span(self, name: str = None, input: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None):
        return _NoOpSpan(name=name, input=input, metadata=metadata)

    def update(self, *args, **kwargs):
        return None


def _get_trace(name: str, metadata: Optional[Dict[str, Any]] = None):
    """Return a real Langfuse trace if available, otherwise a no-op trace.

    This makes tracing resilient when the installed `langfuse` SDK version
    doesn't expose `trace()` or when the client initialization fails.
    """
    if _langfuse is None:
        return _NoOpTrace(name=name, metadata=metadata)
    
    try:
        trace_fn = getattr(_langfuse, "trace", None)
        if callable(trace_fn):
            try:
                return trace_fn(name=name, metadata=metadata)
            except Exception as e:
                logger.warning(f"Failed to create Langfuse trace: {e}")
                return _NoOpTrace(name=name, metadata=metadata)
    except Exception as e:
        logger.warning(f"Error accessing Langfuse trace method: {e}")
    return _NoOpTrace(name=name, metadata=metadata)

def _build_metadata(
    session_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}
    if session_id is not None:
        metadata["session_id"] = session_id
    if contract_id is not None:
        metadata["contract_id"] = contract_id
    if agent_name is not None:
        metadata["agent_name"] = agent_name
    if extra:
        metadata.update(extra)
    return metadata


@contextmanager
def traced_operation(
    name: str,
    input_data: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
):
    """
    Wraps a unit of work in a Langfuse trace + span.

    Captures:
    - input payload
    - latency (ms)
    - custom metadata: session_id, contract_id, agent_name
    - any explicit output passed via span.update(...)
    """
    start_time = time.time()
    metadata = _build_metadata(session_id, contract_id, agent_name, extra_metadata)

    trace = _get_trace(name=name, metadata=metadata)
    span = trace.span(name=name, input=input_data or {}, metadata=metadata)

    try:
        yield span
        duration_ms = int((time.time() - start_time) * 1000)
        span.update(metadata={**metadata, "latency_ms": duration_ms})
        span.end()
        trace.update()
        # Flush data to ensure it's sent (important for short-lived applications)
        if _langfuse is not None:
            try:
                _langfuse.flush()
            except Exception as e:
                logger.debug(f"Failed to flush Langfuse data: {e}")
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        span.update(
            output={"error": str(e)},
            metadata={**metadata, "latency_ms": duration_ms},
        )
        span.end()
        trace.update()
        # Flush even on error
        if _langfuse is not None:
            try:
                _langfuse.flush()
            except Exception:
                pass
        raise


def flush_langfuse() -> None:
    """
    Explicitly flush all pending Langfuse data to ensure it's sent.
    Call this at the end of your application to ensure all traces are uploaded.
    """
    if _langfuse is not None:
        try:
            _langfuse.flush()
            logger.debug("Langfuse data flushed successfully")
        except Exception as e:
            logger.warning(f"Failed to flush Langfuse data: {e}")


def log_llm_usage(span, response) -> None:
    """
    Helper to attach token usage / cost information to a Langfuse span.
    Tries to be defensive about different client versions.
    """
    try:
        usage = getattr(response, "usage", None)
        response_metadata = getattr(response, "response_metadata", None)
        cost = getattr(response, "cost", None)

        usage_dict: Dict[str, Any] = {}
        if usage is not None:
            if hasattr(usage, "model_dump"):
                usage_dict["usage"] = usage.model_dump()
            else:
                usage_dict["usage"] = dict(usage) if hasattr(usage, "items") else str(usage)

        if response_metadata is not None:
            if hasattr(response_metadata, "model_dump"):
                usage_dict["response_metadata"] = response_metadata.model_dump()
            else:
                usage_dict["response_metadata"] = (
                    dict(response_metadata)
                    if hasattr(response_metadata, "items")
                    else str(response_metadata)
                )

        if cost is not None:
            usage_dict["cost"] = cost

        if usage_dict:
            span.update(metadata=usage_dict)
    except Exception:
        # Tracing must never break the main flow
        return
