import argparse
import json
import os
import uuid

from .image_parser import parse_contract_image
from .agents.contextualization_agent import ContextualizationAgent
from .agents.change_extraction_agent import ChangeExtractionAgent
from .models import ContractChangeOutput
from .tracing import traced_operation, flush_langfuse

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Autonomous Contract Comparison and Change Extraction Agent"
    )
    parser.add_argument(
        "--original",
        required=True,
        help="Path to original contract image (PNG/JPEG).",
    )
    parser.add_argument(
        "--amendment",
        required=True,
        help="Path to amendment contract image (PNG/JPEG).",
    )
    parser.add_argument(
        "--session-id",
        required=False,
        help="Optional session identifier for tracing/observability.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Derive a session_id and a simple contract_id from CLI arguments if not provided
    session_id = args.session_id or str(uuid.uuid4())
    contract_id = os.path.splitext(os.path.basename(args.original))[0]

    with traced_operation(
        "main_workflow",
        {
            "original_path": args.original,
            "amendment_path": args.amendment,
        },
        session_id=session_id,
        contract_id=contract_id,
        agent_name="main",
    ) as span:
        # 1. Parse both images (each call is individually traced)
        original_doc = parse_contract_image(
            args.original,
            session_id=session_id,
            contract_id=contract_id,
        )
        amendment_doc = parse_contract_image(
            args.amendment,
            session_id=session_id,
            contract_id=contract_id,
        )

        # 2. Agent 1: contextualization
        ctx_agent = ContextualizationAgent()
        context_analysis = ctx_agent.run(
            original_doc,
            amendment_doc,
            session_id=session_id,
            contract_id=contract_id,
        )

        # 3. Agent 2: change extraction (+ validation traced internally)
        change_agent = ChangeExtractionAgent()
        change_output: ContractChangeOutput = change_agent.run(
            original_doc,
            amendment_doc,
            context_analysis,
            session_id=session_id,
            contract_id=contract_id,
        )

        # 4. Print validated output as JSON
        result = change_output.model_dump()
        span.update(output=result)
        print(json.dumps(result, indent=2))
    
    # Ensure all Langfuse data is flushed before exit
    flush_langfuse()


if __name__ == "__main__":
    main()
