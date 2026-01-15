from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import shutil
import sqlite3
import datetime
from typing import Optional

# Import our modules
from generate_lyrics import get_lyrics, parse_time
from lyrics_fetcher import search_lyrics, get_lyrics_by_id, parse_lrc
from audio_fetcher import download_audio, trim_audio, cleanup_file, search_videos, download_audio_by_url
from main import generate_video

app = FastAPI()

# Setup Directories and DB
OUTPUT_DIR = "generated_files"
DB_NAME = "generations.db"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

if not os.path.exists("static"):
    os.makedirs("static")

# Initialize DB


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  song TEXT, 
                  artist TEXT, 
                  filename TEXT, 
                  created_at TIMESTAMP)''')
    conn.commit()
    conn.close()


init_db()

# Mount generated files
app.mount("/generated", StaticFiles(directory=OUTPUT_DIR), name="generated")


class GenerateRequest(BaseModel):
    song: str
    artist: str
    start_time: str
    end_time: str
    lofi: int = 1
    fontsize: int = 400
    bgcolor: str = "#FFFFFF"
    video_id: Optional[str] = None
    lyrics_id: Optional[int] = None
    manual_lrc: Optional[str] = None


@app.get("/")
async def read_index():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return HTMLResponse("<h1>Brat Generator API is running. Please create static/index.html</h1>")


@app.get("/history_page")
async def read_history_page():
    if os.path.exists("static/history.html"):
        return FileResponse("static/history.html")
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


@app.post("/generate")
async def generate_brat_video(req: GenerateRequest):
    print(f"Received request: {req}")

    # 1. Setup paths with unique timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_song = "".join([c for c in req.song if c.isalnum()
                        or c in (' ', '-', '_')]).strip()
    base_name = f"{safe_song}_{timestamp}"

    output_json = os.path.join(OUTPUT_DIR, f"{base_name}.json")
    output_audio = os.path.join(OUTPUT_DIR, f"{base_name}.mp3")
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
            raise HTTPException(status_code=404, detail="Lyrics not found")

        sliced_lyrics = []
        for line in full_lyrics:
            t = line['start']
            if t >= start_seconds and t <= end_seconds:
                sliced_lyrics.append({
                    "start": round(line['start'] - start_seconds, 2),
                    "text": line['text']
                })

        if not sliced_lyrics:
            raise HTTPException(
                status_code=400, detail="No lyrics in time range")

        import json
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(sliced_lyrics, f)

    except Exception as e:
        print(f"Lyrics Error: {e}")
        raise HTTPException(status_code=500, detail=f"Lyrics Error: {str(e)}")

    # 3. Process Audio
    try:
        temp_audio = None
        if req.video_id:
            # Construct URL from ID (assuming YouTube)
            video_url = f"https://www.youtube.com/watch?v={req.video_id}"
            temp_audio = download_audio_by_url(
                video_url, temp_filename=f"temp_{timestamp}")
        else:
            # Fallback to search
            query = f"{req.artist} - {req.song} audio"
            temp_audio = download_audio(
                query, temp_filename=f"temp_{timestamp}")

        if not temp_audio:
            raise HTTPException(
                status_code=500, detail="Audio download failed")

        success = trim_audio(temp_audio, output_audio,
                             start_seconds, end_seconds)

        # Cleanup temp
        cleanup_file(temp_audio)

        if not success:
            raise HTTPException(status_code=500, detail="Audio trim failed")

    except Exception as e:
        print(f"Audio Error: {e}")
        raise HTTPException(status_code=500, detail=f"Audio Error: {str(e)}")

    # 4. Generate Video
    try:
        generate_video(
            audio_path=output_audio,
            output_path=output_video,
            lyrics_path=output_json,
            bg_color_hex=req.bgcolor,
            max_font_size=req.fontsize,
            lofi_factor=req.lofi
        )
    except Exception as e:
        print(f"Video Gen Error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Video Generation Error: {str(e)}")

    # 5. Log to DB
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("INSERT INTO history (song, artist, filename, created_at) VALUES (?, ?, ?, ?)",
                  (req.song, req.artist, f"{base_name}.mp4", datetime.datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")  # Non-critical

    return {"video_url": f"/generated/{base_name}.mp4"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
