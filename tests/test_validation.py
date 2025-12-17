import pytest
from src.models import ContractChangeOutput


def test_contract_change_output_valid():
    data = {
        "sections_changed": ["2.1", "5.3"],
        "topics_touched": ["payment terms", "liability"],
        "summary_of_the_change": "The amendment updates payment deadlines and caps liability for indirect damages.",
    }
    out = ContractChangeOutput.model_validate(data)
    assert out.sections_changed == ["2.1", "5.3"]
    assert "payment terms" in out.topics_touched


@pytest.mark.parametrize(
    "bad_data",
    [
        {
            # empty sections_changed
            "sections_changed": [],
            "topics_touched": ["payment terms"],
            "summary_of_the_change": "Change in payment schedule.",
        },
        {
            # empty topics_touched
            "sections_changed": ["2.1"],
            "topics_touched": [],
            "summary_of_the_change": "Change in payment schedule.",
        },
        {
            # summary too short
            "sections_changed": ["2.1"],
            "topics_touched": ["payment terms"],
            "summary_of_the_change": "Too short",
        },
    ],
)
def test_contract_change_output_invalid(bad_data):
    with pytest.raises(Exception):
        ContractChangeOutput.model_validate(bad_data)
