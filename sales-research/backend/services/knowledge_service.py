import os
import logging
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self, index_name: str = "sales-intelligence"):
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        # Match glial-index 1536 dimensions
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=1536)
        self.index_name = index_name
        self.index = self.pc.Index(self.index_name)
        
    def _get_vectorstore(self, namespace: str):
        return PineconeVectorStore(
            index=self.index,
            embedding=self.embeddings,
            namespace=namespace
        )

    def ingest_markdown_file(self, file_path: str, namespace: str, metadata: Optional[dict] = None):
        """
        Ingests a markdown file into a specific Pinecone namespace with table awareness.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found.")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by headers for better semantic context
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        md_header_splits = markdown_splitter.split_text(content)

        # Further split if chunks are too large, but increase size to keep tables intact
        # Using a larger chunk size for tables to avoid breaking row structures
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=100,
            separators=["\n\n", "\n", "|", " ", ""] # Prioritize table pipe separators
        )
        splits = text_splitter.split_documents(md_header_splits)

        # Add metadata
        for doc in splits:
            if metadata:
                doc.metadata.update(metadata)
            doc.metadata["source"] = os.path.basename(file_path)

        vectorstore = self._get_vectorstore(namespace)
        vectorstore.add_documents(splits)
        logger.info(f"Ingested {len(splits)} chunks from {file_path} into namespace '{namespace}'")
        return len(splits)

    def retrieve_context(self, query: str, namespace: str, k: int = 3) -> str:
        """
        Retrieves the top k chunks from a specific namespace and formats them as a string.
        """
        vectorstore = self._get_vectorstore(namespace)
        docs = vectorstore.similarity_search(query, k=k)
        
        context_parts = []
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "Unknown")
            header = doc.metadata.get("Header 1") or doc.metadata.get("Header 2") or ""
            context_parts.append(f"--- [Source: {source} | {header}] ---\n{doc.page_content}")

        return "\n\n".join(context_parts)

    def get_index_stats(self) -> dict:
        """
        Returns stats about the index, including vector counts per namespace.
        """
        stats = self.index.describe_index_stats()
        return stats.to_dict()

    def search_all_namespaces(self, query: str, namespaces: List[str], k: int = 2) -> str:
        """
        Searches across multiple namespaces and aggregates the context.
        """
        aggregated_context = []
        for ns in namespaces:
            context = self.retrieve_context(query, ns, k=k)
            if context.strip():
                aggregated_context.append(f"=== KNOWLEDGE TYPE: {ns.upper()} ===\n{context}")
        
        return "\n\n".join(aggregated_context)
