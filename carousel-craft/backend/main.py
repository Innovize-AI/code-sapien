import os
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Carousel Craft AI Engine")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "carousel-craft-backend"}

@app.post("/generate-carousel")
async def generate_carousel(text: str = None, audio: UploadFile = File(None)):
    # 1. If audio, transcribe using Whisper
    # 2. Extract key points and "hooks"
    # 3. Generate slide content (10 slides)
    # 4. Return slide content for frontend preview
    return {
        "slides": [
            {"id": 1, "content": "Welcome to Carousel Craft", "type": "hook"},
            {"id": 2, "content": "Loading your ideas...", "type": "content"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
