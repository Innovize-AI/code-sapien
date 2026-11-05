"""
Shared infrastructure for agent nodes.

_db_ctx: ContextVar injected by pipeline.py before graph invocation.
         Lets node functions access the DB session without passing it explicitly.

KNOWLEDGE_THRESHOLD: minimum Pinecone score for a knowledge match to be used.
"""

from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession

# Set by pipeline.py before invoking the LangGraph graph each turn
_db_ctx: ContextVar[AsyncSession] = ContextVar("lead_agent_db")

KNOWLEDGE_THRESHOLD = 0.60
PORTFOLIO_THRESHOLD = 0.65
RESOURCE_THRESHOLD  = 0.70
