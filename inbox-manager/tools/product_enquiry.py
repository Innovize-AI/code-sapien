from langchain_core.tools import tool
from workflow.state import AgentGraphState
from utils import get_qdrant_as_retriver
from langchain.tools.retriever import create_retriever_tool
# @tool("product_enquiry")
# def product_enquiry(question:str):
#     '''use when the query is related to product or service enquiry (eg: how you can help us, pricing, setup requirements, integrations  )'''

#     retriever= get_qdrant_as_retriver("inbox-manager")

#     relevent_documents= retriever.get_relevant_documents(question)


#     #implement a rag system
#     return f"innovize ai helps business automate processes with ai agnets and ml models"

# @tool("integrations")
# def get_integrations(processed_email_body:str):
#     '''use when the query is related to integrations  )'''
#     return f"yes our solutions integrate with various platforms"


def get_product_enquiry_tool():

    """when the query is related to product(or service) enquiry"""
    from langchain.tools.retriever import create_retriever_tool

    retriever= get_qdrant_as_retriver("inbox-manager")
    print("called product enquiry tool")
    product_enquiry_tool = create_retriever_tool(
        retriever,
        "product_enquiry",
        "use when the query is related to product or service enquiry (eg: how you can help us, pricing, setup requirements, integrations  )",
    )
    return product_enquiry_tool.as_tool()

