import os
import logging
import json
from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db import get_db, get_report
from db.models import Profile, CopilotChatLog
from db.crud import get_org_settings
from dependencies import get_current_user
from models.gemini_models import get_gemini_model
from services.knowledge_service import KnowledgeService
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

logger = logging.getLogger(__name__)
router = APIRouter(tags=['Lead Copilot'])

class ChatHistoryMessage(BaseModel):
    role: str # 'user' or 'assistant'
    text: str
    sources: List[Dict[str, str]] = []

class CopilotChatRequest(BaseModel):
    message: str

@router.get("/reports/{report_id}/chat/history")
async def get_copilot_chat_history(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Retrieves previous Copilot chat history for a specific report."""
    try:
        report = await get_report(db, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Research report not found")
        
        # Access control
        if report.organization_id != current_user.organization_id and str(report.created_by_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Unauthorized access to this report.")
        
        # Load from DB
        stmt = select(CopilotChatLog).where(CopilotChatLog.report_id == UUID(report_id)).order_by(CopilotChatLog.created_at.asc())
        res = await db.execute(stmt)
        logs = res.scalars().all()
        
        history = [
            ChatHistoryMessage(
                role=log.sender_type,
                text=log.message_text,
                sources=log.sources if log.sources else []
            )
            for log in logs
        ]
        return {"messages": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch chat history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reports/{report_id}/chat")
async def copilot_chat(
    report_id: str,
    req: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Sends a message to the AI Copilot for a specific lead report, with web search grounding."""
    try:
        # 1. Fetch unified research report
        report = await get_report(db, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Research report not found")
        
        # Access control
        if report.organization_id != current_user.organization_id and str(report.created_by_id) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Unauthorized access to this report.")
        
        # 2. Fetch past Copilot chat logs to populate RAG context history
        stmt = select(CopilotChatLog).where(CopilotChatLog.report_id == UUID(report_id)).order_by(CopilotChatLog.created_at.asc())
        res = await db.execute(stmt)
        logs = res.scalars().all()
        
        chat_history = []
        for log in logs:
            if log.sender_type == "user":
                chat_history.append(HumanMessage(content=log.message_text))
            else:
                chat_history.append(AIMessage(content=log.message_text))

        # 3. Retrieve relevant sales playbooks / case studies from Pinecone (RAG)
        settings_info = await get_org_settings(db, user_id=str(current_user.id), org_id=current_user.organization_id)
        index_name = settings_info.pinecone_index_name if settings_info and settings_info.pinecone_index_name else "glial-index"
        
        kb_context = ""
        try:
            ks = KnowledgeService(index_name=index_name)
            context_strings = []
            for ns in ["playbooks", "solutions", "case-studies"]:
                ns_context = ks.retrieve_context(
                    query=req.message,
                    namespace=ns,
                    user_id=str(current_user.id),
                    index_name=index_name
                )
                if ns_context and "No initially similar knowledge found" not in ns_context:
                    context_strings.append(ns_context)
            kb_context = "\n\n".join(context_strings)
        except Exception as pe:
            logger.warning(f"RAG search failed in Copilot Chat: {pe}")

        # 4. Formulate Prompt Context
        system_prompt = f"""
        You are the Glial Lead Copilot, a sales strategy AI assistant helping a representative prepare for sales outreach or review a deal.
        You have deep, structured context about the lead, their company, their pain points, and previous interactions.

        --- LEAD DETAILS ---
        Full Name: {report.fullname or 'N/A'}
        Email: {report.email_id or 'N/A'}
        LinkedIn: {report.linkedin_url or 'N/A'}
        Website: {report.website or 'N/A'}
        Lead Score: {report.lead_score or 0}/100
        Project Urgency: {report.project_urgency or 0}/100
        
        --- COMPANY NAME & STATS ---
        Company: {report.company_name or 'N/A'}
        Details: {report.company_stats or 'N/A'}
        
        --- RE/ID OR B2B RESEARCH SUMMARY REPORT ---
        {report.sales_research_report or 'N/A'}
        
        --- TARGET PAIN POINTS ---
        {report.target_pain_points or 'N/A'}
        
        --- STRATEGIC OUTREACH ANGLE ---
        {report.strategic_solutions or 'N/A'}
        
        --- EMAIL/REPLY CONVERSATION HISTORY ---
        {report.email_history or 'No email history/replies recorded yet.'}

        --- INTERNAL KNOWLEDGE BASE (RAG) ---
        {kb_context or 'No relevant internal sales playbooks found.'}

        INSTRUCTIONS:
        - Analyze the lead context and answer the representative's questions strategically.
        - Give specific recommendations, copy suggestions, and action steps.
        - If the representative asks you queries requiring external, real-time web lookups (e.g. competitor pricing, recent press releases, company events, target market shifts), use your Google Search tool to search the web.
        - Respond concisely and professionally.
        """

        # 5. Build messages array
        messages = [SystemMessage(content=system_prompt)]
        messages.extend(chat_history)
        messages.append(HumanMessage(content=req.message))

        # 6. Save the user's message to the database
        user_log = CopilotChatLog(
            report_id=UUID(report_id),
            sender_type="user",
            message_text=req.message
        )
        db.add(user_log)
        await db.flush()

        # 7. Generate Response
        llm = get_gemini_model(temperature=0.2, model='gemini-3-flash-preview', enable_search=True)
        response = await llm.ainvoke(messages)
        
        # Extract text from response content
        if isinstance(response.content, list):
            answer_text = ""
            for item in response.content:
                if isinstance(item, dict) and "text" in item:
                    answer_text += item["text"]
                elif isinstance(item, str):
                    answer_text += item
                else:
                    answer_text += str(item)
        else:
            answer_text = str(response.content)
        
        # Parse grounding metadata/sources
        sources = []
        if hasattr(response, "response_metadata") and "raw_response" in response.response_metadata:
            raw = response.response_metadata["raw_response"]
            if hasattr(raw, "candidates") and raw.candidates:
                gm = raw.candidates[0].grounding_metadata
                if gm and gm.grounding_chunks:
                    for chunk in gm.grounding_chunks:
                        if chunk.web:
                            sources.append({
                                "title": chunk.web.title or "Web Search Source",
                                "uri": chunk.web.uri or ""
                            })
                            
        # 8. Save Assistant's response to the database
        assistant_log = CopilotChatLog(
            report_id=UUID(report_id),
            sender_type="assistant",
            message_text=answer_text,
            sources=sources
        )
        db.add(assistant_log)
        await db.commit()

        return {
            "answer": answer_text,
            "sources": sources
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in copilot_chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
