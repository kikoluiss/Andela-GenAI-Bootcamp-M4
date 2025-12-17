import base64
import json
import mimetypes
import sys
from pathlib import Path
from typing import List, Optional

from .models import ParsedDocument, ParsedSection
from .tracing import traced_operation, log_llm_usage
from .utils import get_openai_client, extract_response_content, extract_json_from_response
from .config import DEFAULT_MODEL


def _encode_image_to_base64(image_path: str) -> str:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _guess_mime_type(image_path: str) -> str:
    mime, _ = mimetypes.guess_type(image_path)
    if not mime:
        mime = "image/png"
    return mime


def parse_contract_image(
    image_path: str,
    session_id: Optional[str] = None,
    contract_id: Optional[str] = None,
) -> ParsedDocument:
    """
    Uses a multimodal LLM to parse a scanned contract image into structured sections.
    Traced with Langfuse as an "image_parsing" operation.
    """
    with traced_operation(
        "image_parsing",
        {"image_path": image_path},
        session_id=session_id,
        contract_id=contract_id,
        agent_name="image_parser",
    ) as span:
        image_b64 = _encode_image_to_base64(image_path)
        mime_type = _guess_mime_type(image_path)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a legal document parser. "
                    "Extract the contract into a JSON array of sections. "
                    "Each section must have: identifier, title (if present), and text. "
                    "Identifiers should follow the document's hierarchy (e.g., '1', '1.1', '2.3')."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Extract structured sections from this contract image.",
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{image_b64}",
                    },
                ],
            },
        ]

        client = get_openai_client()
        response = client.responses.create(
            model=DEFAULT_MODEL,
            input=messages,
        )

        # Attach token usage / cost to the span
        log_llm_usage(span, response)

        # Extract and parse JSON from response
        try:
            content = extract_response_content(response)
            span.update(output={"raw_response": content})
            raw_sections = extract_json_from_response(content)
        except (ValueError, json.JSONDecodeError) as e:
            # Print the response content for debugging so we can see what the model returned
            content = extract_response_content(response) if 'content' not in locals() else content
            print("[DEBUG] Failed to parse JSON from model response. Content repr:", repr(content), file=sys.stderr)
            span.update(output={"parse_error": str(e), "response_repr": repr(response)})
            raise

        sections: List[ParsedSection] = []
        for s in raw_sections:
            identifier = s.get("identifier", "")
            title = s.get("title")
            text = s.get("text") or ""
            # Ensure text meets minimum length required by ParsedSection.
            if len(text.strip()) < 10:
                # Try to use title as fallback, otherwise use a placeholder.
                text = (title or "").strip()
                if len(text) < 10:
                    text = "No content available."

            sections.append(
                ParsedSection(identifier=identifier, title=title, text=text)
            )

        doc = ParsedDocument(filename=str(image_path), sections=sections)
        span.update(output={"num_sections": len(sections)})
        return doc
