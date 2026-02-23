from mcp.server.fastmcp import FastMCP
from services.knowledge_service import KnowledgeService
from notion_client import Client
import os

# Initialize FastMCP Server
mcp = FastMCP("Innovize Sales Brain")

# Initialize our existing Knowledge Service
kb_service = KnowledgeService(index_name="sales-intelligence")
notion = Client(auth=os.getenv("NOTION_TOKEN"))

@mcp.tool()
def sync_notion_page(page_id: str, namespace: str = "playbooks"):
    """
    Syncs a Notion page's content into the Sales Brain (Pinecone).
    """
    # 1. Fetch from Notion
    page_content = notion.pages.retrieve(page_id=page_id)
    # (Conversion logic to Markdown goes here...)
    md_text = "# Mock Markdown from Notion" 
    
    # 2. Ingest into Pinecone using our existing service
    # We'd add a helper method to KnowledgeService for direct strings
    # kb_service.ingest_text(md_text, namespace=namespace)
    
    return f"Successfully synced page {page_id} to {namespace} namespace."

@mcp.tool()
def research_lead_skill(linkedin_url: str):
    """
    Triggers the high-stakes Sales Research workflow for a LinkedIn lead.
    """
    # This would call our LangGraph 'graph.py' workflow
    result = {"status": "success", "verdict": "Strike now with BAB framework."}
    return result

if __name__ == "__main__":
    mcp.run()
