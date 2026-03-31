import json
import logging

logger = logging.getLogger(__name__)
from pydantic import BaseModel, Field
from typing import List, Optional
from agents.report_agent import get_gemini_model
from langchain_core.messages import SystemMessage, HumanMessage

class DocumentMetadata(BaseModel):
    industry: str = Field(description="Primary industry this document pertains to (e.g., SaaS, Finance, Healthcare)")
    product: str = Field(description="Name of the product or service discussed")
    category: str = Field(description="Type of content: playbook, case-study, or solution-guide")
    target_persona: List[str] = Field(description="Job titles or roles this document is targeting")
    key_pain_points: List[str] = Field(description="Pain points addressed in this document")
    suggested_namespace: str = Field(description="One of: playbooks, case-studies, solutions")

class DocumentClassifier:
    def __init__(self):
        self.llm = get_gemini_model(model="gemini-3-flash-preview", temperature=0)

    async def classify_document(self, content: str, filename: str) -> DocumentMetadata:
        """
        Analyzes markdown content and returns structured metadata.
        """
        prompt = f"""
        Analyze the following Knowledge Base document (Filename: {filename}) and extract key metadata.
        
        ### DOCUMENT CONTENT:
        {content[:4000]} # Limit to 4k tokens for classification
        
        ### INSTRUCTIONS:
        1. Identify the primary industry.
        2. Identify the product name (e.g., Glial, IDP).
        3. Determine if this is a 'playbook' (how-to/strategy), 'case-study' (success story/ROI), or 'solution' (technical specs).
        4. List target roles (e.g., CTO, VP Sales).
        5. Map to one of the three namespaces: 'playbooks', 'case-studies', or 'solutions'.
        """
        
        structured_llm = self.llm.with_structured_output(DocumentMetadata)
        
        messages = [
            SystemMessage(content="You are a professional sales consultant and Knowledge Base Architect."),
            HumanMessage(content=prompt)
        ]
        
        try:
            result = await structured_llm.ainvoke(messages)
            return result
        except Exception as e:
            logger.info(f"Error classifying document {filename}: {e}")
            # Fallback
            return DocumentMetadata(
                industry="General",
                product="Unknown",
                category="unsorted",
                target_persona=[],
                key_pain_points=[],
                suggested_namespace="solutions"
            )

# Singleton instance
document_classifier = DocumentClassifier()
