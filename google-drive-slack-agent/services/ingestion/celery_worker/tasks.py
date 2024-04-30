
from ast import List
import os
from celery import shared_task
from langchain_core.documents import Document
import googledocs as GoogleDocsLoader
import googlesheets as GoogleSheetsLoader

from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import qdrant
from langchain_community.embeddings.huggingface import HuggingFaceEmbeddings
from qdrant_client.http import models as rest



@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5},
             name='load_doc:load_document_from_id_task')
def load_document_from_id_task(id, creds ):
        """Load a document from an ID."""
        from io import BytesIO

        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaIoBaseDownload

 
        document= GoogleDocsLoader.load_data_from_document_id(id,creds)
        # print(document)
        metadata = {
            "source": f"https://docs.google.com/document/d/{id}/edit",
            # "title": f"{file.get('name')}",
            # "when": f"{file.get('modifiedTime')}",
        }
        doc= Document(page_content=document,metadata=metadata)

        # data_embed_ingest_task.apply_async(
        #             args=(doc), 
        #             queue="embed_ingest"
        #         )
        # print(doc.page_content)
        
        task= data_embed_ingest_task.delay([doc])
        print(task.id)
        print(task.backend)
        # return Document(page_content=document, metadata=metadata)
        

@shared_task(autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5},
             name='embed_ingest:data_embed_ingest_task')
             
def data_embed_ingest_task(doc):

    '''
    Chunk data and ingest into vector store
    '''
    embeddings= OpenAIEmbeddings(model="text-embedding-3-small", api_key= os.environ.get("OPEN_API_SECRET"))
#     embeddings = HuggingFaceEmbeddings(
#     model_name="sentence-transformers/all-mpnet-base-v2"
# )


    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    splits = text_splitter.split_documents(doc)
    print(len(splits))
    from qdrant_client import QdrantClient
    from langchain_community.vectorstores.qdrant import Qdrant

    collection_name = "gdrive-collection"

    client = QdrantClient()

    # client.create_collection(collection_name=collection_name, vectors_config={
    #     "content": rest.VectorParams(
    #         distance=rest.Distance.COSINE,
    #         size=1536,
    #     ),
    # },)
    qd = Qdrant(client, collection_name, embeddings)

    qd.from_documents(documents=splits,embedding=embeddings,collection_name=collection_name)


    # index document
    from langchain.indexes import SQLRecordManager, index

    namespace = f"gdrive/{collection_name}"
    record_manager = SQLRecordManager(
    namespace, db_url="sqlite:///record_manager_cache.sql")

    record_manager.create_schema()
    
    # Create the index
    result= index(doc,record_manager,qd,cleanup="incremental",source_id_key="source",)

    print(result)
    return result

@shared_task(bind=True,autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5},
             name='load_doc:load_doc_task')

def load_doc_task(val):  
      return val







    


    








    
