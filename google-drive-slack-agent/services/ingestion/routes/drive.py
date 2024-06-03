import os
from urllib import response
from dotenv import load_dotenv
from fastapi import BackgroundTasks, APIRouter
from fastapi.responses import JSONResponse
from googledrive import GoogleDriveLoader
from celery_worker import utils
from celery_worker.tasks import load_doc_task

from celery.result import AsyncResult

# load env variables from env file
load_dotenv()
 

GOOGLE_DRIVE_ID=os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
cwd=os.getcwd()


router = APIRouter(prefix='/drive', tags=['Drive'], responses={404: {"description": "Not found"}})

def get_task_info(task_id):
    """
    return task info for the given task_id
    """

    task_result =  AsyncResult(task_id)
    print("task_result" , task_result.state)
    result = {
        "task_id": task_id,
        "task_status": task_result.state,
        "task_result": task_result.result
    }
    return result


@router.post("/load")
async def get_load_doc():
    task= load_doc_task.delay()
    return JSONResponse({"task_id":task.id})

@router.get("/task/{task_id}")
async def get_task_status(task_id: str) -> dict:
    """
    Return the status of the submitted Task
    """
    print("task_id " , task_id)
    result= get_task_info(task_id)
        
    return JSONResponse(result)

@router.post("/ingest")
async def ingest_documents(background_tasks: BackgroundTasks):
   return background_tasks.add_task(ingest_and_index)
    

def ingest_and_index():
    # Install unstructured if not already installed
    try:
        import unstructured
    except ImportError:
        import subprocess
        subprocess.check_call(["pip", "install", "unstructured"])
        import unstructured
    # Load documents from Google Drive
    # print(os.path.join(os.path.dirname(__file__), '..', '.credentials', 'keys.json'))

    loader = GoogleDriveLoader(
        folder_id=GOOGLE_DRIVE_ID,
        # document_ids=["1h1dVnclOrZ35JSC3xZXhqu0Zu9xXeNuNQoRauW9K0ek"],
        file_types=["document"],
        recursive=True,
        service_account_key=os.path.join( cwd,'.credentials', 'keys.json')
    )

    
    documents = loader.load()
   
    print(f"Indexed documents from Google Drive.")

@router.post("/ingest-document-by-id")
def ingest_document_by_id(document_id:str):
    return

@router.post("/configure-notification")
def configure_notifications(folder_id: str, topic_id: str):
    
    loader = GoogleDriveLoader(
        folder_id=GOOGLE_DRIVE_ID,
        # document_ids=["1h1dVnclOrZ35JSC3xZXhqu0Zu9xXeNuNQoRauW9K0ek"],
        file_types=["document"],
        recursive=True,
        service_account_key=os.path.join( cwd,'.credentials', 'keys.json')
    )

    return loader.configure_notifications(folder_id,topic_id)

@router.get("/get-drive-changes")
async def get_drive_changes():
     
     loader = GoogleDriveLoader(
        folder_id=GOOGLE_DRIVE_ID,
        # document_ids=["1h1dVnclOrZ35JSC3xZXhqu0Zu9xXeNuNQoRauW9K0ek"],
        file_types=["document"],
        recursive=True,
        service_account_key=os.path.join( cwd,'.credentials', 'keys.json')
    )
     response= await loader.fetch_changes()

     return response
