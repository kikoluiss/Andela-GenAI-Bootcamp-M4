from typing import Any, Dict, Optional

from langchain_core.runnables import RunnableLambda, RunnableSequence

from .agents.contextualization_agent import ContextualizationAgent
from .agents.change_extraction_agent import ChangeExtractionAgent
from .models import ParsedDocument, ContractChangeOutput
from .config import DEFAULT_MODEL


def build_agent_pipeline(model: str = DEFAULT_MODEL) -> RunnableSequence:
    """
    Build a LangChain Runnable pipeline that orchestrates Agent 1 and Agent 2.

    Inputs to the pipeline should be a dict with:
    - "original_doc": ParsedDocument
    - "amendment_doc": ParsedDocument
    - Optional: "session_id", "contract_id"

    The pipeline will:
    1) Call ContextualizationAgent (Agent 1) to produce `context_analysis`.
    2) Call ChangeExtractionAgent (Agent 2) to produce a ContractChangeOutput.
    """
    ctx_agent = ContextualizationAgent(model=model)
    change_agent = ChangeExtractionAgent(model=model)

    def add_context(inputs: Dict[str, Any]) -> Dict[str, Any]:
        original: ParsedDocument = inputs["original_doc"]
        amendment: ParsedDocument = inputs["amendment_doc"]
        session_id: Optional[str] = inputs.get("session_id")
        contract_id: Optional[str] = inputs.get("contract_id")

        context = ctx_agent.run(
            original,
            amendment,
            session_id=session_id,
            contract_id=contract_id,
        )
        # carry original inputs forward and attach context_analysis
        return {**inputs, "context_analysis": context}

    def run_change(inputs: Dict[str, Any]) -> ContractChangeOutput:
        original: ParsedDocument = inputs["original_doc"]
        amendment: ParsedDocument = inputs["amendment_doc"]
        session_id: Optional[str] = inputs.get("session_id")
        contract_id: Optional[str] = inputs.get("contract_id")
        context_analysis: Dict[str, Any] = inputs["context_analysis"]

        return change_agent.run(
            original,
            amendment,
            context_analysis,
            session_id=session_id,
            contract_id=contract_id,
        )

    pipeline: RunnableSequence = RunnableSequence(
        RunnableLambda(add_context),
        RunnableLambda(run_change),
    )
    return pipeline


def run_agent_pipeline(
    original_doc: ParsedDocument,
    amendment_doc: ParsedDocument,
    session_id: Optional[str] = None,
    contract_id: Optional[str] = None,
    model: str = DEFAULT_MODEL,
) -> ContractChangeOutput:
    """
    Convenience helper that builds the LangChain pipeline and immediately invokes it.

    Example:
        from src.image_parser import parse_contract_image
        from src.orchestrator import run_agent_pipeline

        original_doc = parse_contract_image("data/test_contracts/contract1_original.png")
        amendment_doc = parse_contract_image("data/test_contracts/contract1_amendment.png")

        result = run_agent_pipeline(original_doc, amendment_doc)
    """
    chain = build_agent_pipeline(model=model)
    return chain.invoke(
        {
            "original_doc": original_doc,
            "amendment_doc": amendment_doc,
            "session_id": session_id,
            "contract_id": contract_id,
        }
    )
