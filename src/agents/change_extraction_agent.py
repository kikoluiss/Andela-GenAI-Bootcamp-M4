from typing import Dict, Any, Optional

from ..models import ParsedDocument, ContractChangeOutput
from ..tracing import traced_operation, log_llm_usage
from ..utils import get_openai_client, extract_response_content, extract_json_from_response, serialize_document
from ..config import DEFAULT_MODEL


class ChangeExtractionAgent:
    """
    Agent 2: uses Agent 1's contextualized alignment to extract the concrete changes.
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = get_openai_client()

    def run(
        self,
        original: ParsedDocument,
        amendment: ParsedDocument,
        context_analysis: Dict[str, Any],
        session_id: Optional[str] = None,
        contract_id: Optional[str] = None,
    ) -> ContractChangeOutput:
        """
        Returns a validated ContractChangeOutput object.

        The LLM call and the validation step are individually traced.
        """
        # --- LLM call for change extraction ---
        with traced_operation(
            "agent_change_extraction",
            {"context_analysis": context_analysis},
            session_id=session_id,
            contract_id=contract_id,
            agent_name="ChangeExtractionAgent",
        ) as span:
            system_prompt = (
                "You are Agent 2 (Change Extraction Agent) for contract comparison.\n"
                "You receive:\n"
                "1) The original and amended contract texts.\n"
                "2) A JSON analysis from Agent 1 aligning sections and describing structural changes.\n\n"
                "Your task:\n"
                "- Identify which sections actually changed (text modified, added, or removed).\n"
                "- Identify which legal/business topics are touched by these changes (e.g., payment terms, liability, confidentiality).\n"
                "- Write a concise but precise summary of the changes.\n\n"
                "Return ONLY a JSON object with:\n"
                "{\n"
                '  \"sections_changed\": [list of section identifiers],\n'
                '  \"topics_touched\": [list of topics],\n'
                '  \"summary_of_the_change\": \"string summary\"\n'
                "}\n"
            )

            user_content = (
                "AGENT 1 CONTEXTUALIZATION (JSON):\n"
                f"{context_analysis}\n\n"
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
            raw = extract_json_from_response(content)
            span.update(output={"raw_llm_output": raw})

        # --- Validation step as its own traced operation ---
        with traced_operation(
            "validation",
            {"raw_output": raw},
            session_id=session_id,
            contract_id=contract_id,
            agent_name="ChangeExtractionAgent",
            extra_metadata={"stage": "pydantic_validation"},
        ) as vspan:
            output = ContractChangeOutput.model_validate(raw)
            vspan.update(output=output.model_dump())

        return output
