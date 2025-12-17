from src.models import ParsedDocument, ParsedSection, ContractChangeOutput
from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.change_extraction_agent import ChangeExtractionAgent


class DummyContent:
    def __init__(self, text: str):
        self.text = text


class DummyOutput:
    def __init__(self, text: str):
        self.content = [DummyContent(text)]


class DummyResponse:
    def __init__(self, text: str):
        self.output = [DummyOutput(text)]


def test_agent_handoff(monkeypatch):
    """
    Agent handoff test: verifies that
    - Agent 1 (ContextualizationAgent) returns a structured JSON object
    - The same object is passed as `context_analysis` into Agent 2.
    Network calls to the LLM are mocked.
    """

    original = ParsedDocument(
        filename="original",
        sections=[
            ParsedSection(identifier="1", title="Fees", text="Customer pays 10,000 USD per month."),
        ],
    )
    amendment = ParsedDocument(
        filename="amendment",
        sections=[
            ParsedSection(identifier="1", title="Fees", text="Customer pays 13,500 USD per month."),
        ],
    )

    fake_ctx = {
        "aligned_sections": [
            {"original_id": "1", "amendment_id": "1", "relation": "modified"},
        ],
        "structural_notes": "Section 1 fees were modified.",
    }

    # Mock Agent 1's LLM call inside ContextualizationAgent
    import json

    def fake_create(self, model, input, response_format):
        return DummyResponse(json.dumps(fake_ctx))

    class DummyResponses:
        def create(self, model, input, response_format="json"):
            return fake_create(self, model, input, response_format)

    ctx_agent = ContextualizationAgent()
    # Mock the client instance's responses attribute
    ctx_agent.client.responses = DummyResponses()
    ctx_result = ctx_agent.run(original, amendment)
    assert ctx_result == fake_ctx

    # Now ensure Agent 2 receives the same context_analysis
    def fake_change_run(self, orig, amend, context_analysis):
        assert context_analysis == fake_ctx
        return ContractChangeOutput(
            sections_changed=["1"],
            topics_touched=["fees"],
            summary_of_the_change="Fees in section 1 increased from 10,000 to 13,500 USD per month.",
        )

    monkeypatch.setattr(ChangeExtractionAgent, "run", fake_change_run)

    change_agent = ChangeExtractionAgent()
    out = change_agent.run(original, amendment, ctx_result)

    assert isinstance(out, ContractChangeOutput)
    assert out.sections_changed == ["1"]
    assert "fees" in out.topics_touched
