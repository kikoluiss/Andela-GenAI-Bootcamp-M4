from typing import Dict, Any, Optional

from ..models import ParsedDocument
from ..tracing import traced_operation, log_llm_usage
from ..utils import get_openai_client, extract_response_content, extract_json_from_response, serialize_document
from ..config import DEFAULT_MODEL

class ContextualizationAgent:
    """
    Agent 1: reads both documents, understands structure,
    identifies corresponding sections.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = get_openai_client()

    def run(
        self,
        original: ParsedDocument,
        amendment: ParsedDocument,
        session_id: Optional[str] = None,
        contract_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Returns a JSON-like dict describing:
        - aligned_sections: list of {original_id, amendment_id, relation}
        - structural_notes: description of structure and differences

        Execution is traced with Langfuse as "agent_contextualization".
        """
        with traced_operation(
            "agent_contextualization",
            {
                "original_sections": [s.identifier for s in original.sections],
                "amendment_sections": [s.identifier for s in amendment.sections],
            },
            session_id=session_id,
            contract_id=contract_id,
            agent_name="ContextualizationAgent",
        ) as span:
            system_prompt = (
                "You are Agent 1 (Contextualization Agent) for contract comparison.\n"
                "You are given the structured sections of an original contract and its amendment.\n"
                "Your tasks:\n"
                "1. Understand the structure of both documents.\n"
                "2. Align corresponding sections between the original and the amendment.\n"
                "3. Identify which sections appear new, deleted, or moved.\n"
                "Return a JSON object with:\n"
                "- aligned_sections: list of {original_id, amendment_id, relation}\n"
                "- structural_notes: string\n"
            )

            user_content = (
                "ORIGINAL CONTRACT:\n"
                f"{serialize_document(original)}\n\n"
                "AMENDMENT:\n"
                f"{serialize_document(amendment)}"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]

            response = self.client.responses.create(
                model=self.model,
                input=messages,
            )

            # Attach token usage / cost
            log_llm_usage(span, response)

            # Extract and parse JSON from response
            content = extract_response_content(response)
            structured = extract_json_from_response(content)
            span.update(output=structured)
            return structured
