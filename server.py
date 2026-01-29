from lyrics_fetcher import search_lyrics, get_lyrics_by_id, parse_lrc
from main import generate_video
from audio_fetcher import trim_audio, cleanup_file, search_videos, download_audio_by_url
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import shutil
import sqlite3
import datetime
import asyncio
import uuid
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import sys

# Import our modules
from generate_lyrics import get_lyrics, parse_time

from lyrics_fetcher import search_lyrics, get_lyrics_by_id, parse_lrc
from audio_fetcher import first_audio, trim_audio, cleanup_file, search_videos, download_audio_by_url
from main import generate_video

# --- Job Queue Structures ---


class Job(BaseModel):
    id: str
    status: str  # 'queued', 'processing', 'completed', 'failed'
    position: int = 0
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float
    request_payload: Optional['GenerateRequest'] = None


job_queue: asyncio.Queue = asyncio.Queue()
job_store: Dict[str, Job] = {}

# --- Background Worker ---


async def worker():
    print("Worker started, waiting for jobs...")
    while True:
        job_id = await job_queue.get()
        job = job_store.get(job_id)

        if not job:
            job_queue.task_done()
            continue

        try:
            print(f"Processing job {job_id}")
            job.status = "processing"

            # Extract request data attached to the job object (we'll attach it dynamically)
            req = getattr(job, "request_payload", None)

            if req:
                # Run the synchronous generation in a separate thread
                video_url = await asyncio.to_thread(process_video_generation, req)
                job.result = video_url
                job.status = "completed"
            else:
                job.status = "failed"
                job.error = "No payload found"

        except Exception as e:
            print(f"Job {job_id} failed: {e}")
            job.status = "failed"
            job.error = str(e)
        finally:
            job_queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start worker on startup
    asyncio.create_task(worker())
    yield
    # Clean up if needed

app = FastAPI(lifespan=lifespan)

# Setup Directories and DB
OUTPUT_DIR = "generated_files"
DB_NAME = "generations.db"
MEDIA_DIR = "media"
TEMP_DIR = "temp"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

if not os.path.exists("static"):
    os.makedirs("static")

if not os.path.exists(MEDIA_DIR):
    os.makedirs(MEDIA_DIR)

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# Initialize DB


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  song TEXT, 
                  artist TEXT,
                  audio TEXT,
                  filename TEXT, 
                  created_at TIMESTAMP)''')
    conn.commit()
    conn.close()


init_db()

# Mount generated files
# Mount generated files
app.mount("/generated", StaticFiles(directory=OUTPUT_DIR), name="generated")
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

# # Mount static files (using resource path)
# static_path = get_resource_path("static")
# if os.path.exists(static_path):
app.mount("/static", StaticFiles(directory="static"), name="static")


class GenerateRequest(BaseModel):
    song: str
    artist: str
    start_time: str
    end_time: str
    lofi: int = 1
    fontsize: int = 400
    bgcolor: str = "#FFFFFF"
    textcolor: str = "#000000"
    video_id: Optional[str] = None
    lyrics_id: Optional[int] = None
    manual_lrc: Optional[str] = None
    textcolor: str = "#000000"


@app.get("/")
async def read_index():
    index_path = get_resource_path("static/index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Brat Generator API is running. Please create static/index.html</h1>")


@app.get("/history_page")
async def read_history_page():
    history_path = get_resource_path("static/history.html")
    if os.path.exists(history_path):
        return FileResponse(history_path)
    return HTMLResponse("<h1>History page not found. Please create static/history.html</h1>")


@app.get("/history")
async def get_history():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM history ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/search/video")
async def search_video_endpoint(q: str):
    results = search_videos(q)
    return results


@app.get("/search/lyrics")
async def search_lyrics_endpoint(q: str):
    results = search_lyrics(q)
    return results


@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Calculate queue position if queued
    if job.status == "queued":
        # This is O(N) but queue likely short.
        # For production execution, better data structures exist, but this is fine for local.
        # We assume queue order matches creation time for simplicity.
        # Actually simplest way: iterate the internal deque if accessible, or just count 'queued' jobs created before this one.
        # Let's just estimate based on job_store creation times of other queued jobs
        queued_jobs = [j for j in job_store.values(
        ) if j.status == 'queued' and j.created_at < job.created_at]
        job.position = len(queued_jobs) + 1
    else:
        job.position = 0

    return job


@app.post("/generate")
async def queue_generate_request(req: GenerateRequest):
    job_id = str(uuid.uuid4())
    import time
    job = Job(id=job_id, status="queued",
              created_at=time.time(), request_payload=req)

    # Attach payload dynamically to avoid polluting BaseModel if valid (or just use a wrapper)
    # Python allows arbitrary attributes on objects but Pydantic might restrict it depending on config.
    # Let's just store the payload in a parallel dict or just use a helper method.
    # Let's attach to the job instance.
    # setattr(job, "request_payload", req) # Now handled in constructor

    job_store[job_id] = job
    await job_queue.put(job_id)

    return {"job_id": job_id, "status": "queued"}


def process_video_generation(req: GenerateRequest):
    print(f"Starting generation for {req.song}")

    # 1. Setup paths with unique timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_song = "".join([c for c in req.song if c.isalnum()
                        or c in (' ', '-', '_')]).strip()
    base_name = f"{safe_song}_{timestamp}"

    output_json = os.path.join(TEMP_DIR, f"{base_name}.json")
    output_audio = os.path.join(TEMP_DIR, f"{base_name}.mp3")
    output_video = os.path.join(OUTPUT_DIR, f"{base_name}.mp4")

    # 2. Process Lyrics
    try:
        start_seconds = parse_time(req.start_time)
        end_seconds = parse_time(req.end_time)

        full_lyrics = None
        if req.manual_lrc:
            print("Using Manual LRC content")
            full_lyrics = parse_lrc(req.manual_lrc)
        elif req.lyrics_id:
            print(f"Fetching lyrics by ID: {req.lyrics_id}")
            full_lyrics = get_lyrics_by_id(req.lyrics_id)
        else:
            print(f"Fetching lyrics by search: {req.artist} - {req.song}")
            full_lyrics = get_lyrics(req.artist, req.song)

        if not full_lyrics:
            raise Exception("Lyrics not found")

        sliced_lyrics = []
        for line in full_lyrics:
            t = line['start']
            if t >= start_seconds and t <= end_seconds:
                sliced_lyrics.append({
                    "start": round(line['start'] - start_seconds, 2),
                    "text": line['text']
                })

        if not sliced_lyrics:
            raise Exception("No lyrics in time range")

        import json
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(sliced_lyrics, f)

    except Exception as e:
        print(f"Lyrics Error: {e}")
        raise e

    # 3. Process Audio
    try:
        temp_audio = None

        if not req.video_id:
            query = f"{req.artist} - {req.song} audio"
            req.video_id = first_audio(query)

        exists = False
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute(
                "SELECT EXISTS(SELECT 1 FROM history WHERE audio = ?)", (req.video_id,))
            exists = bool(c.fetchone()[0])
            conn.close()
        except Exception as e:
            print(f"DB Error: {e}")
            raise e

        temp_audio_path = os.path.join(MEDIA_DIR, req.video_id)  # type: ignore
        if not exists:
            video_url = f"https://www.youtube.com/watch?v={req.video_id}"
            temp_audio = download_audio_by_url(
                video_url, temp_filename=temp_audio_path)
        else:
            temp_audio = f"{temp_audio_path}.mp3"

        if not temp_audio:
            raise Exception("Audio download failed")

        success = trim_audio(temp_audio, output_audio,
                             start_seconds, end_seconds)

        if not success:
            raise Exception("Audio trim failed")

    except Exception as e:
        print(f"Audio Error: {e}")
        raise e

    # 4. Generate Video
    try:
        generate_video(
            audio_path=output_audio,
            output_path=output_video,
            lyrics_path=output_json,
            bg_color_hex=req.bgcolor,
            text_color_hex=req.textcolor,
            max_font_size=req.fontsize,
            lofi_factor=req.lofi,
        )
    except Exception as e:
        print(f"Video Gen Error: {e}")
        raise e

    # 5. Log to DB
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO history (song, artist, audio, filename, created_at) VALUES (?, ?, ?, ?, ?)",
                  (req.song, req.artist, req.video_id, f"{base_name}.mp4", datetime.datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")  # Non-critical

    cleanup_file(output_audio)
    cleanup_file(output_json)

    return f"/generated/{base_name}.mp4"


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
