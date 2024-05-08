from pathlib import Path
import time
from celery import current_app
from celery.result import AsyncResult
from dotenv import load_dotenv

import os
from fastapi import FastAPI
from routes.drive import router

from celery_worker.utils import create_celery 

import sys
# Add sibling_folder to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))


def create_app() -> FastAPI:
    current_app=FastAPI(title="App with Celery and RabbitMQ")
    current_app.celery_app =  create_celery()
    current_app.include_router(router)
    return current_app

app = create_app()
celery = app.celery_app


# @app.middleware("http")
# async def add_process_time_header(request, call_next):
#     print('inside middleware!')
#     start_time = time.time()
#     response = await call_next(request)
#     process_time = time.time() - start_time
#     response.headers["X-Process-Time"] = str(f'{process_time:0.4f} sec')
#     return response


NUM_WORKERS = int(os.environ.get("NUM_WORKERS", 4))  # Number of parallel workers



# @app.get("/")
# def app_status():
#     return "App is healthy"

# @app.post("/ingest")
# async def ingest_documents(background_tasks: BackgroundTasks):
#     background_tasks.add_task(ingest_and_index)
#     return {"message": "Ingestion process started"}

# def ingest_and_index():
#     # Install unstructured if not already installed
#     try:
#         import unstructured
#     except ImportError:
#         import subprocess
#         subprocess.check_call(["pip", "install", "unstructured"])
#         import unstructured
#     # Load documents from Google Drive
#     # print(os.path.join(os.path.dirname(__file__), '..', '.credentials', 'keys.json'))

#     loader = GoogleDriveLoader(
#         folder_id=GOOGLE_DRIVE_ID,
#         # document_ids=["1h1dVnclOrZ35JSC3xZXhqu0Zu9xXeNuNQoRauW9K0ek"],
#         file_types=["document"],
#         recursive=True,
#         service_account_key=os.path.join( cwd,'.credentials', 'keys.json')
#     )

    

#     documents = loader.load()
#     # for doc in documents:
#     #     print(doc)
#     # Create the index
#     # index_creator = VectorstoreIndexCreator(
#     #     vectorstore=vector_store,
#     #     text_splitter=text_splitter,
#     #     embedding=embeddings,
#     #     delete_mode="incremental",
#     # )

#     # Ingest documents in parallel
#     # with Pool(processes=NUM_WORKERS) as pool:
#     #     indexes = pool.map(index_creator.from_documents, chunk_documents(documents, NUM_WORKERS))

#     # # Merge the indexes
#     # index = index_creator.merge_indexes(indexes)

#     print(f"Indexed documents from Google Drive.")

# def chunk_documents(documents, num_chunks):
#     chunk_size = len(documents) // num_chunks
#     for i in range(num_chunks):
#         start = i * chunk_size
#         end = start + chunk_size
#         yield documents[start:end]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)