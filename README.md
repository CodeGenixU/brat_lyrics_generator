# Brat Lyrics Generator

A Python-based tool that generates "brat" aesthetic lyric videos with a Lo-Fi pixelated style. It features a full web interface for searching songs, selecting specific lyric lines, and managing generation history.

![Project Screenshot](https://github.com/user-attachments/assets/52a89c3d-be4c-4747-bd11-e7246c5ed33e)

## Features

- **Spotify-Style Search**: Search for any song to find matching YouTube audio and LRCLIB synchronized lyrics.
- **Precision Selection**:
    - Choose the exact YouTube audio track.
    - Choose the exact Lyrics version.
    - **Line-by-Line Selection**: Click start and end lines to automatically set the video timestamps.
- **Manual Mode**: Paste your own `.lrc` content if the search results aren't perfect.
- **Customizable Aesthetics**:
    - Adjustable "Lo-Fi" pixelation factor.
    - Dynamic font sizing.
    - Custom background colors.
- **History Tracking**: View and redownload previously generated videos.
- **Brat Styling**: Defaults to the iconic slime green (`#8ace00`) and low-res aesthetic.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/brat-lyrics-generator.git
    cd brat_lyrics_generator
    ```

2.  **Install Dependencies**:
    Ensure you have Python installed, then run:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: You may need to install `fastapi`, `uvicorn`, `requests`, `yt-dlp`, `moviepy`, and `imageio-ffmpeg` if they are not all in your requirements file.*

3.  **FFmpeg**:
    This project uses `moviepy` and `imageio-ffmpeg`. Usually, the binary is handled automatically, but ensure you have a working FFmpeg setup if you encounter issues.

## Usage

1.  **Start the Server**:
    ```bash
    python server.py
    ```
    The server will start at `http://0.0.0.0:8000`.

2.  **Open the Web Interface**:
    Navigate to `http://localhost:8000` in your browser.

3.  **Generate a Video**:
    - **Search**: Enter "Song - Artist" (e.g., "Kushagra - Finding her").
    - **Select**: Click a video card and a lyrics card.
    - **Refine**: In the third column, select the range of lyrics you want to capture.
    - **Customize**: Adjust Lo-Fi (1-20), Font Size, or Background Color.
    - **Generate**: Click "GENERATE VIDEO".

4.  **Download**:
    Click the download link when ready, or visit the `[HISTORY]` page to find it later.

## Screenshots

### Search & Selection Interface
![Search Interface](https://github.com/user-attachments/assets/4dea8139-32b8-4f11-8186-e20aaee310c5)
*Search for songs and select specific versions.*

### Line Selection
![Line Selection](https://github.com/user-attachments/assets/ffadb03a-9f89-40f0-b6c0-8d249a45415d)
*Interactive line selector for perfect timing.*

### Generated Output Example
![Generated Video](https://github.com/user-attachments/assets/c1c5e5e7-a3e2-4207-b2d9-34afe3a38464)
*Example of the final lo-fi lyric video.*

## Project Structure

- `server.py`: FastAPI backend handling API requests and serving static files.
- `static/`: Frontend HTML/CSS/JS files (`index.html`, `history.html`).
- `fetchers/`: Modules for retrieving content (`audio_fetcher.py`, `lyrics_fetcher.py`).
- `main.py` & `generate_lyrics.py`: Core logic for video rendering and lyric processing.
- `generated_files/`: Directory where output videos are saved.
- `generations.db`: SQLite database storing generation history.

## Contributing

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.
