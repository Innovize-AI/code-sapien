import os
import re
import logging
import asyncio
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from services.document_classifier import document_classifier

logger = logging.getLogger(__name__)

# Per-namespace chunking config.
# case-studies: large chunks so each full case study stays atomic.
# playbooks: medium chunks so each section (script, objection table, workflow block) stays whole.
# solutions: medium chunks for product descriptions / pricing tables.
_NAMESPACE_CHUNK_CONFIG: dict[str, dict] = {
    "case-studies": {"chunk_size": 2000, "chunk_overlap": 300},
    "playbooks":    {"chunk_size": 1500, "chunk_overlap": 200},
    "solutions":    {"chunk_size": 1500, "chunk_overlap": 200},
}
_DEFAULT_CHUNK_CONFIG = {"chunk_size": 1500, "chunk_overlap": 200}

# Headers used for the first-pass split.  H3 is intentionally omitted for
# case-studies so that Challenge/Solution/Results/Features all remain inside
# the same parent chunk.
_HEADERS_ALL = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
_HEADERS_H2_ONLY = [("#", "Header 1"), ("##", "Header 2")]


def _prepend_breadcrumb(doc: Document) -> Document:
    """
    Prepend the section breadcrumb (H1 > H2 > H3) to the chunk text so that
    retrieved chunks are self-contained even without metadata inspection.
    """
    parts = []
    for key in ("Header 1", "Header 2", "Header 3"):
        val = doc.metadata.get(key)
        if val:
            parts.append(val)
    if parts:
        breadcrumb = " > ".join(parts)
        doc.page_content = f"[{breadcrumb}]\n\n{doc.page_content}"
    return doc


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

    def _chunk_documents(self, docs: List[Document], namespace: str) -> List[Document]:
        """
        Second-pass splitter that respects table boundaries.

        Tables (contiguous lines starting with '|') are never split — the
        entire table block is treated as one unit.  Only prose/lists that
        exceed the chunk_size threshold are further divided.

        Key fix: '|' is NOT a separator (it destroyed markdown tables previously).
        """
        cfg = _NAMESPACE_CHUNK_CONFIG.get(namespace, _DEFAULT_CHUNK_CONFIG)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=cfg["chunk_size"],
            chunk_overlap=cfg["chunk_overlap"],
            # Never split on '|' — that shreds markdown tables into individual cells.
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        results: List[Document] = []
        for doc in docs:
            if len(doc.page_content) <= cfg["chunk_size"]:
                # Already small enough — keep as-is (most sections will land here).
                results.append(doc)
                continue

            # Protect table blocks: replace each table with a sentinel token,
            # split the remaining prose, then restore the table text.
            table_pattern = re.compile(
                r"((?:^\|.+\n?)+)",  # one or more contiguous '|'-led lines
                re.MULTILINE,
            )
            table_store: dict[str, str] = {}

            def stash_table(m: re.Match) -> str:
                key = f"__TABLE_{len(table_store)}__"
                table_store[key] = m.group(0)
                return key

            protected = table_pattern.sub(stash_table, doc.page_content)
            sub_docs = splitter.split_documents([Document(page_content=protected, metadata=doc.metadata)])

            # Restore tables
            for sub in sub_docs:
                for key, table_text in table_store.items():
                    sub.page_content = sub.page_content.replace(key, table_text)
                results.append(sub)

        return results

    async def ingest_markdown_file(self, file_path: str, namespace: Optional[str] = None, metadata: Optional[dict] = None):
        """
        Ingests a markdown file into a specific Pinecone namespace with auto-classification.

        Chunking strategy:
        - First pass: MarkdownHeaderTextSplitter on H1/H2 (H3 only for non-case-study files).
          This keeps each section (outreach angle, case study, SOP step) as one unit.
        - Breadcrumb: parent headers are prepended to each chunk's text so retrieved
          chunks are self-contained without metadata inspection.
        - Second pass: RecursiveCharacterTextSplitter fires ONLY on chunks that still
          exceed the size limit, using paragraph/sentence boundaries — never '|'.
          Tables are stashed before splitting and restored after.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found.")

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Auto-classify if metadata/namespace is missing or enrichment needed
        if namespace is None or metadata is None:
            doc_meta = await document_classifier.classify_document(content, os.path.basename(file_path))
            logger.info(f"doc_meta: {doc_meta}")
            if namespace is None:
                namespace = doc_meta.suggested_namespace
            if metadata is None:
                metadata = doc_meta.dict()
            else:
                metadata.update(doc_meta.dict())

        # 2. First-pass: header-based split
        # case-studies: split only on H1/H2 so each full case study (with all its
        # H3 sub-sections) remains one document before the size check.
        headers = _HEADERS_H2_ONLY if namespace == "case-studies" else _HEADERS_ALL
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers)
        md_header_splits = markdown_splitter.split_text(content)

        # 3. Prepend breadcrumb to every chunk
        md_header_splits = [_prepend_breadcrumb(doc) for doc in md_header_splits]

        # 4. Second-pass: table-safe size-based split (only fires when chunk > limit)
        splits = self._chunk_documents(md_header_splits, namespace)

        # 5. Attach file-level metadata
        for doc in splits:
            if metadata:
                doc.metadata.update(metadata)
            doc.metadata["source"] = os.path.basename(file_path)

        # 6. Ingest
        vectorstore = self._get_vectorstore(namespace)
        vectorstore.add_documents(splits)
        logger.info(f"Ingested {len(splits)} chunks from {file_path} into namespace '{namespace}' with metadata: {metadata}")
        return {"chunks": len(splits), "namespace": namespace, "metadata": metadata}

    def retrieve_context(self, query: str, namespace: str, k: int = 3) -> str:
        """
        Retrieves the top k chunks from a specific namespace and formats them as a string.
        """
        vectorstore = self._get_vectorstore(namespace)
        docs = vectorstore.similarity_search(query, k=k)

        context_parts = []
        for doc in docs:
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

    def retrieve_from_files(self, filenames: List[str], query: str, k: int = 5) -> str:
        """
        Retrieves context specifically from a list of files across all namespaces.
        """
        namespaces = ["playbooks", "case-studies", "solutions"]
        aggregated_context = []

        for ns in namespaces:
            try:
                vectorstore = self._get_vectorstore(ns)
                filter_dict = {"source": {"$in": filenames}}
                docs = vectorstore.similarity_search(query, k=k, filter=filter_dict)

                if docs:
                    aggregated_context.append(f"=== MATCHES IN {ns.upper()} ===")
                    for doc in docs:
                        source = doc.metadata.get("source", "Unknown")
                        header = doc.metadata.get("Header 1") or doc.metadata.get("Header 2") or ""
                        aggregated_context.append(f"--- [Source: {source} | {header}] ---\n{doc.page_content}")
            except Exception as e:
                logger.warning(f"Error searching namespace {ns} with filter: {e}")
                continue

        return "\n\n".join(aggregated_context)
