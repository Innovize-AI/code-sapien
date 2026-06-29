from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class KnowledgeSource(BaseModel):
    source: str = Field(description="The file name or asset type used for this reasoning.")
    snippet: str = Field(description="Specific text snippet retrieved from the knowledge base.")

class UnifiedCommand(BaseModel):
    verdict: str = Field(description=(
        "A single, prescriptive one-sentence command for the sales rep. "
        "Format depends on tier:\n"
        "- TIER 1 (score ≤40): 'Stop work — [specific disqualifying data point from research]. [Optional revisit condition].'\n"
        "- TIER 2 (score 41-65): 'Monitor — [exact missing signal]. [Specific trigger to revisit].'\n"
        "- TIER 3 (score ≥66): Prescriptive strike command citing the specific product and signal.\n"
        "BANNED for Tier 1/2: any phrase suggesting an outreach sequence, validation sequence, curiosity-based approach, or action steps. "
        "Always cite a concrete data point (e.g., job title, company size, a specific post date/content, score value) — never paraphrase vaguely."
    ))
    framework_selected: str = Field(description="The messaging framework used (e.g., AIDA, PAS, BAB).")
    framework_reasoning: str = Field(description="Why this specific framework (AIDA, PAS, BAB) was chosen for this lead's persona.")
    timing_advice: str = Field(description="Strategic advice on when to strike (e.g., 'Green Light', 'Hold for 48h', 'Avoid').")
    product_selection_reasoning: str = Field(description="Explicit justification for why a specific product or service (e.g., AI Transformation vs. Glial) was chosen as the lead offering.")
    strategic_reasoning: str = Field(description="""The logic behind the verdict, cross-referencing research and playbooks.
    - Do not write message drafts. Focus 100% on logic.
    - `advanced_strategic_pivots`: Provide 2-3 "If/Then" scenarios. (e.g., "If they engage with the 'manual tax' insight, offer a free workflow audit of their post-merger reporting layers").
    - WEIGHTED TONE: Professional, calm, 7th-grade reading level.
    """)
    objection_preemption: List[str] = Field(description="Specific potential objections to handle in the outreach.")
    sources: List[KnowledgeSource] = Field(description="The specific Knowledge Base assets used to validate this command.")

class NextStepBlueprint(BaseModel):
    """The strategic blueprint for a single outreach touchpoint (CSO defined)."""
    engagement_type: Literal["LI_WARM", "LI_COMMENT", "LI_INVITE", "LI_DM", "EMAIL_DIRECT", "EMAIL_FOLLOWUP", "BREAK_UP_EMAIL", "CALL"] = Field(
        description="The exact engagement channel and action type."
    )
    delay_days: int = Field(
        description="Days to wait AFTER the previous step. Step 1 is usually 0 or -1 (for warming)."
    )
    trigger: Literal["always", "if_no_reply"] = Field(
        description="Condition to execute this step."
    )
    narrative_angle: str = Field(
        description="The psychological stage or creative angle of this step (e.g., 'warm_up', 'surface_the_gap', 'deepen_the_cost')."
    )
    reference_signal: str = Field(
        description="The specific research signal (URL/Title) that anchors this step."
    )
    internal_note: str = Field(
        description="Strategic intent for this step. Guidance for the Outreach Agent on what tone and specific evidence to use."
    )
    cta_type: Optional[Literal["INTEREST_BASED", "TIME_BASED", "REFERRAL", "SOFT_CLOSE"]] = Field(
        None,
        description="The type of call-to-action to use for this step."
    )

class NextStep(NextStepBlueprint):
    """The fully drafted outreach touchpoint (Outreach Designer populated)."""
    draft: str = Field(
        description="The main body of the email or LinkedIn message. This MUST contain the primary copy (the hook, the bridge, and the proof points). Do not leave this empty."
    )
    email_subject: Optional[str] = Field(
        None,
        description="The winning subject line (only for EMAIL steps). 3-7 words, lowercase, non-salesy."
    )
    subject_line_variants: List[str] = Field(
        default_factory=list,
        description="2-3 alternative subject line hooks (e.g., 'Show You Know Me', '3-part Internal', 'Question')."
    )
    preview_text: Optional[str] = Field(
        None,
        description="Optimized first 100 characters for mobile notifications."
    )
    ps_line: Optional[str] = Field(
        None,
        description="High-impact pattern interrupt or social proof snippet for the end of the email."
    )
    cta_type: Optional[Literal["INTEREST_BASED", "TIME_BASED", "REFERRAL", "SOFT_CLOSE"]] = Field(
        None,
        description="The type of call-to-action used, mapped to the awareness stage."
    )
    sources: List[KnowledgeSource] = Field(
        default_factory=list,
        description="The specific Knowledge Base assets (playbook name and snippet) used to ground this specific step copy."
    )

class OutreachBlueprint(BaseModel):
    """The strategic sequence blueprint generated by the CSO."""
    variant_name: str = Field(description="Unique name for this variant (e.g., 'Strategic Pivot', 'Solution Angle B').")
    primary_pain_point: str = Field(description="The single pain point being targeted across every step. Never changes mid-sequence.")
    sequence_theme: str = Field(description="One sentence describing the narrative arc (e.g. 'Build conviction that manual reporting overhead is costing the team an invisible FTE').")
    prospect_current_stage: Literal[
        "UNAWARE",
        "PROBLEM_AWARE",
        "COST_AWARE",
        "SOLUTION_AWARE",
        "VENDOR_AWARE"
    ] = Field(
        description="""
        The awareness stage the prospect is at RIGHT NOW, inferred from their signals.
        - UNAWARE: No relevant posts, no pain signals, no engagement with related content.
        - PROBLEM_AWARE: Posted about the pain, commented on related content, mentioned the struggle explicitly.
        - COST_AWARE: Hiring for roles that address the gap, news about related operational issues, mentioned business impact.
        - SOLUTION_AWARE: Downloaded content, visited high-value pages, attended webinars, requested demo.
        - VENDOR_AWARE: Inbound inquiry, direct demo request, form submission, actively evaluating tools.
        The sequence MUST start from this stage. Do not go back and re-teach stages they have already passed.
        """
    )
    stage_detection_reasoning: str = Field(
        description="One sentence explaining exactly which signal from the research determined the prospect's current awareness stage."
    )
    steps: List[NextStepBlueprint] = Field(
        description="Ordered steps starting FROM the prospect's current stage. Do not include stages they have already passed."
    )
    exit_strategy: str = Field(
        default="Archive and review in 90 days.",
        description="Exact action if the entire sequence gets no reply (e.g. 'No reply by Day 24: archive, set 90-day re-check')."
    )

class OutreachSequence(BaseModel):
    """The final, fully drafted outreach sequence."""
    variant_name: str = Field(description="Unique name for this variant.")
    primary_pain_point: str = Field(description="The single pain point being targeted.")
    sequence_theme: str = Field(description="The narrative arc theme.")
    steps: List[NextStep] = Field(description="Ordered list of fully drafted steps.")
    sources: List[KnowledgeSource] = Field(
        default_factory=list,
        description="The specific Knowledge Base assets (playbook name and snippet) used to ground this entire sequence."
    )
    exit_strategy: str = Field(
        default="Archive and review in 90 days.",
        description="What to do if the entire sequence fails."
    )

class MultiOutreachSequence(BaseModel):
    """Container for multiple drafted sequences (A/B testing)."""
    sequences: List[OutreachSequence]

class GlobalCSOBriefing(BaseModel):
    selected_product_name: str = Field(description="The final product or service selected as the primary offering for this lead.")
    selected_product_justification: str = Field(description="Why this specific product is the best fit for the identified pain points.")
    strategic_pivot_usecase: Optional[str] = Field(
        None,
        description="A highly specific, concrete usecase or strategic vertical application (e.g., 'Automated bill of lading parsing' or 'Contract digitization') if a Strategic Pivot product is selected. Set to None/N/A if not a Strategic Pivot."
    )
    unified_command: UnifiedCommand
    executive_blueprint_summary: str = Field(description="A high-level synthesis of why this account matters.")
    refined_linkedin_message: Optional[str] = Field(None, description="The CSO-optimized LinkedIn message.")
    advanced_strategic_pivots: List[str] = Field(
        default_factory=list, 
        description="High-impact 'If/Then' tactical advice for when the prospect engages (e.g., 'If they reply about X, offer Y')."
    )
    refined_email_body: Optional[str] = Field(None, description="The CSO-optimized email body.")
    strategic_proof_points: List[str] = Field(default_factory=list, description="Specific snippets/insights from playbooks to use as 'Proof' in outreach.")
    playbook_examples: List[str] = Field(default_factory=list, description="Direct outreach examples and messaging templates retrieved from internal playbooks.")
    lookalike_peer: Optional[str] = Field(None, description="A peer or competitor company identified from RAG context to use as social proof (e.g., 'We helped [Peer] solve X').")
    outreach_sequences: List[OutreachBlueprint] = Field(
        default_factory=list,
        description="A list of strategic sequence blueprints (1-2 variants) for A/B testing."
    )



