import os
import yt_dlp
from moviepy.audio.io.AudioFileClip import AudioFileClip
import imageio_ffmpeg


def download_audio(query, temp_filename="full_audio"):
    """
    Downloads audio from YouTube using yt-dlp search.
    Returns the path to the downloaded file.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'outtmpl': temp_filename,  # Ensures consistent filename
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    print(f"Searching and downloading audio for: '{query}'...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            # We search for 1 video
            ydl.download([f"ytsearch1:{query}"])
            # The output will be temp_filename.mp3 because of postprocessor
            expected_output = f"{temp_filename}.mp3"
            if os.path.exists(expected_output):
                return expected_output
            else:
                print("Error: Downloaded file not found.")
                return None
        except Exception as e:
            print(f"Error downloading audio: {e}")
            return None


def search_videos(query, limit=5):
    """
    Searches for videos on YouTube and returns metadata.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'extract_flat': True,  # Don't download, just extract info
    }

    results = []
    print(f"Searching YouTube for: '{query}'...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            if 'entries' in info:
                for entry in info['entries']:
                    results.append({
                        'id': entry.get('id'),
                        'title': entry.get('title'),
                        'uploader': entry.get('uploader'),
                        'duration': entry.get('duration'),
                        'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry.get('id')}",
                        # heuristic
                        'thumbnail': f"https://img.youtube.com/vi/{entry.get('id')}/hqdefault.jpg"
                    })
        except Exception as e:
            print(f"Error searching videos: {e}")

    return results


def download_audio_by_url(url, temp_filename="full_audio"):
    """
    Downloads audio from a specific YouTube URL.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'outtmpl': temp_filename,
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    print(f"Downloading audio from: '{url}'...")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
            expected_output = f"{temp_filename}.mp3"
            if os.path.exists(expected_output):
                return expected_output
            else:
                print("Error: Downloaded file not found.")
                return None
        except Exception as e:
            print(f"Error downloading audio: {e}")
            return None


def trim_audio(input_path, output_path, start_time, end_time):
    """
    Trims the audio file to the specified start and end times.
    """
    try:
        print(f"Trimming audio from {start_time}s to {end_time}s...")
        audio = AudioFileClip(input_path)

        # Ensure times are within bounds
        start = max(0, start_time)
        end = min(audio.duration, end_time)

        if start >= end:
            print("Error: Start time is after end time.")
            return False

        trimmed = audio.subclip(start, end)
        trimmed.write_audiofile(output_path, logger=None)

        # Close to release file lock
        audio.close()
        trimmed.close()

        return True
    except Exception as e:
        print(f"Error trimming audio: {e}")
        return False

# Cleanup helper


def cleanup_file(path):
    if os.path.exists(path):
        try:
            os.remove(path)
            print(f"Cleaned up {path}")
        except:
            pass
