import asyncio, hashlib, uuid, os, shutil,time
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from chatbot import invoke as _invoke
from fastapi.templating import Jinja2Templates
from chatbot import restart_chatbot
from helper_function import process_video_pipeline
from job_status import JOB_STATUS, JOB_TIMEOUT

app = FastAPI(title="Video to PDF Transcription")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Mount static files
app.mount("/static", StaticFiles(directory="templates"), name="static")

# Configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'Videos')
PDF_FOLDER = os.path.join(os.getcwd(), 'PDFs')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)


@app.get("/")
async def read_root():
    """Serve the main HTML page"""
    return FileResponse("templates/index.html")



@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Handle video file upload and start processing pipeline
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    try:
        filename = file.filename
        video_path = os.path.join(UPLOAD_FOLDER, filename)

        # Save file
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Create job entry
        job_id = str(uuid.uuid4())
        JOB_STATUS[job_id] = {
            "status": "processing",
            "started_at": time.time(),
            "message": "Processing started"
        }

        # Run pipeline in background
        background_tasks.add_task(
            process_video_pipeline,
            video_path,
            filename,
            job_id
        )

        return {
            "success": True,
            "job_id": job_id,
            "message": "Video uploaded. Processing started."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/html", response_class=HTMLResponse)
async def chat_ui(request: Request):
    return templates.TemplateResponse("chatbot.html", {
        "request": request,
        "title": "Video Analyzer Chatbot"
    })
    
@app.get("/status/{job_id}")
async def get_status(job_id: str):
    job = JOB_STATUS.get(job_id)

    if not job:
        return {"status": "unknown"}

    if job["status"] == "processing":
        if time.time() - job["started_at"] > JOB_TIMEOUT:
            job["status"] = "failed"
            job["message"] = "Processing timed out"

    return job

@app.post("/chatting")
async def chat(request: Request):
    user_query = None
    session_id = None
    try:
        content_type = (request.headers.get("content-type") or "").lower()
        if "application/json" in content_type:
            data = await request.json()
            if isinstance(data, dict):
                user_query = data.get("message")
        elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            user_query = form.get("message") if form else None
        else:
            user_query = request.query_params.get("message")
            if not user_query:
                try:
                    data = await request.json()
                    if isinstance(data, dict):
                        user_query = data.get("message")
                except Exception:
                    try:
                        form = await request.form()
                        user_query = form.get("message") if form else None
                    except Exception:
                        body = await request.body()
                        user_query = body.decode(errors="ignore").strip() if body else None
    except Exception:
        pass
    if user_query:
        user_query = str(user_query).strip()
    
    if not user_query:
        return JSONResponse({"error": "Please enter a message."}, status_code=400)

    session_id = request.headers.get("X-Session-ID", "").strip() or None
    
    if not session_id:
        try:
            if "application/json" in (request.headers.get("content-type") or "").lower():
                body_data = await request.json()
                session_id = (body_data.get("session_id", "").strip() or None) if isinstance(body_data, dict) else None
        except Exception:
            pass
    
    if not session_id:
        session_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()    
    fut_rag = loop.run_in_executor(None, lambda q=user_query: _invoke(q,session_id))
    answer = await fut_rag
    return JSONResponse({
                "reply": answer,
                "session_id": session_id
            }, status_code=200)
        
