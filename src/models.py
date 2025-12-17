from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class ParsedSection(BaseModel):
    identifier: str = Field(..., min_length=1, description="Section or clause identifier")
    title: Optional[str] = Field(None, description="Optional title of the section")
    text: str = Field(..., min_length=10, description="Full text of the section")

class ParsedDocument(BaseModel):
    filename: str
    sections: List[ParsedSection] = Field(default_factory=list)

class ContractChangeOutput(BaseModel):
    sections_changed: List[str] = Field(..., description="List of identifiers for sections or clauses that changed.")
    topics_touched: List[str] = Field(..., description="List of business/legal topics touched by the changes.")
    summary_of_the_change: str = Field(..., min_length=20, description="Natural language summary of the changes.")

    @field_validator("sections_changed")
    @classmethod
    def non_empty_sections(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("sections_changed must contain at least one section identifier")
        return v

    @field_validator("topics_touched")
    @classmethod
    def non_empty_topics(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("topics_touched must contain at least one topic")
        return v

    @field_validator("summary_of_the_change")
    @classmethod
    def summary_not_too_short(cls, v: str) -> str:
        if len(v.strip()) < 20:
            raise ValueError("summary_of_the_change must be at least 20 characters")
        return v