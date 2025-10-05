
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

class DeepResearchRequest(BaseModel):
    query: str
    chat_id: Optional[UUID] = None
    max_concurrent_research_units: Optional[int] = Field(default=1)
    max_researcher_iterations: Optional[int] = Field(default=1)
    max_react_tool_calls: Optional[int] = Field(default=1)
    max_structured_output_retries: Optional[int] = Field(default=1)

class DeepResearchResponse(BaseModel):
    report: str
