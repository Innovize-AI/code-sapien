from http import client
import os
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings
from openai import embeddings
from qdrant_client import QdrantClient
from langchain_community.vectorstores.qdrant import Qdrant
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.tools import Tool

def get_qdrant_as_retriver()-> VectorStoreRetriever:

    embeddings= OpenAIEmbeddings(model="text-embedding-3-small", api_key= os.environ.get("OPEN_API_SECRET"))

    collection_name = "collection_name"
    client= QdrantClient()

    qd = Qdrant(client, collection_name, embeddings)

    retriever= qd.as_retriever()

    return retriever
    # client.create_collection(collection_name=collection_name, vectors_config={
    #     "content": rest.VectorParams(
    #         distance=rest.Distance.COSINE,
    #         size=1536,
    #     ),
    #return qd.as_retriever()


def get_rag_tool()-> Tool:

    from langchain.tools.retriever import create_retriever_tool

    retriever= get_qdrant_as_retriver()    

    tool = create_retriever_tool(
    retriever,
    "data_retriever",
    "Searches and returns data from our data.can be from google drive, pdf etc",
    )
    return tool


