"""
Utility functions shared across the codebase.
"""
import json
import os
from typing import Any, Dict, Optional

from openai import OpenAI

from .models import ParsedDocument


def get_openai_client() -> OpenAI:
    """
    Get a configured OpenAI client instance.
    Centralizes client initialization to avoid duplication.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    return OpenAI(api_key=api_key)


def extract_response_content(response: Any) -> str:
    """
    Extract text content from an OpenAI response object.
    Handles different response formats robustly.

    Args:
        response: OpenAI response object

    Returns:
        Extracted text content as string
    """
    if hasattr(response, "output_text") and response.output_text:
        return response.output_text

    try:
        return response.output[0].content[0].text
    except (AttributeError, IndexError, KeyError):
        return str(response)


def extract_json_from_response(content: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response, handling markdown code fences.

    Args:
        content: Raw response content that may contain JSON wrapped in code fences

    Returns:
        Parsed JSON as dictionary

    Raises:
        json.JSONDecodeError: If JSON parsing fails
        ValueError: If no valid JSON content is found
    """
    c = content.strip()
    if not c:
        raise ValueError("Empty response content")

    # If the model wrapped JSON in markdown code fences, strip them
    if c.startswith("```"):
        parts = c.split("```")
        for p in parts:
            if p.strip():
                # Remove language identifier if present (e.g., "json")
                if p.lstrip().startswith("json"):
                    p = p.split("\n", 1)[1] if "\n" in p else ""
                c = p.strip()
                if c:
                    break

    if not c:
        raise ValueError("No valid JSON content found after stripping code fences")

    return json.loads(c)


def serialize_document(doc: ParsedDocument) -> str:
    """
    Serialize a ParsedDocument to a string format for LLM prompts.

    Args:
        doc: ParsedDocument to serialize

    Returns:
        Formatted string representation of the document
    """
    parts = []
    for sec in doc.sections:
        parts.append(f"{sec.identifier} :: {sec.title or ''}\n{sec.text}\n")
    return "\n\n".join(parts)

