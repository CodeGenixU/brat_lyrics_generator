import argparse
import json
import re
from lyrics_fetcher import get_lyrics


def parse_time(time_str):
    """
    Parses time string to seconds.
    Supports "mm:ss", "m:ss", or plain seconds "ss".
    """
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
    return float(time_str)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and slice lyrics for Brat Generator")
    parser.add_argument("--song", required=True, help="Song Name")
    parser.add_argument("--artist", required=True, help="Artist Name")
    parser.add_argument("--start", required=True,
                        help="Start time (e.g. '0:30' or '30')")
    parser.add_argument("--end", required=True,
                        help="End time (e.g. '1:00' or '60')")
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--audio_output", help="Output Audio file (optional)")

    args = parser.parse_args()

    start_seconds = parse_time(args.start)
    end_seconds = parse_time(args.end)

    print(f"Fetching lyrics for '{args.song}' by '{args.artist}'...")
    print(f"Clipping from {start_seconds}s to {end_seconds}s...")

    full_lyrics = get_lyrics(args.artist, args.song)

    if not full_lyrics:
        print("Failed to fetch lyrics.")
        return

    filtered_lines = []

    for line in full_lyrics:
        t = line['start']
        if t >= start_seconds and t <= end_seconds:
            filtered_lines.append(line)

    if not filtered_lines:
        print("Warning: No lyrics found in the specified time range.")
        sliced_lyrics = []
    else:
        # Re-writing the slice logic here correctly:
        sliced_lyrics = []
        for line in filtered_lines:
            new_time = line['start'] - start_seconds
            sliced_lyrics.append({
                "start": round(new_time, 2),
                "text": line['text']
            })

        if sliced_lyrics:
            print(
                f"Extracted {len(sliced_lyrics)} lines. Timestamps shifted by {start_seconds}s.")

    # Audio Download Execution
    if args.audio_output and sliced_lyrics:
        try:
            from audio_fetcher import download_audio, trim_audio, cleanup_file

            query = f"{args.artist} - {args.song} audio"
            temp_audio = download_audio(query)

            if temp_audio:
                success = trim_audio(
                    temp_audio, args.audio_output, start_seconds, end_seconds)
                if success:
                    print(f"Audio saved to {args.audio_output}")
                cleanup_file(temp_audio)
            else:
                print("Skipping audio trim due to download failure.")
        except ImportError:
            print(
                "Error: audio_fetcher not found or dependencies missing. Cannot download audio.")

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(sliced_lyrics, f, indent=2)

    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
