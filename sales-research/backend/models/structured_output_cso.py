from pydantic import BaseModel, Field
from typing import List, Optional

class KnowledgeSource(BaseModel):
    source: str = Field(description="The file name or asset type used for this reasoning.")
    snippet: str = Field(description="Specific text snippet retrieved from the knowledge base.")

class UnifiedCommand(BaseModel):
    verdict: str = Field(description="A single, prescriptive one-sentence command for the sales rep.")
    framework_selected: str = Field(description="The messaging framework used (e.g., AIDA, PAS, BAB).")
    timing_advice: str = Field(description="Strategic advice on when to strike (e.g., 'Green Light', 'Hold for 48h').")
    strategic_reasoning: str = Field(description="The logic behind the verdict, cross-referencing research and playbooks.")
    objection_preemption: List[str] = Field(description="Specific potential objections to handle in the outreach.")
    sources: List[KnowledgeSource] = Field(description="The specific Knowledge Base assets used to validate this command.")

class GlobalCSOBriefing(BaseModel):
    unified_command: UnifiedCommand
    executive_blueprint_summary: str = Field(description="A high-level synthesis of why this account matters.")
    refined_linkedin_message: Optional[str] = Field(None, description="The CSO-optimized LinkedIn message.")
    refined_email_body: Optional[str] = Field(None, description="The CSO-optimized email body.")
    strategic_proof_points: List[str] = Field(default_factory=list, description="Specific snippets/insights from playbooks to use as 'Proof' in outreach.")
