import requests
import re


def get_lyrics(artist, song_name):
    """
    Fetches synchronized lyrics from LRCLIB.net
    Returns list of dicts: [{'start': 0.0, 'text': 'Lyric line...'}, ...]
    """
    url = "https://lrclib.net/api/search"
    params = {
        "q": f"{song_name} {artist}"
    }

    try:
        response = requests.get(url, params=params)
        print(response.url)
        response.raise_for_status()
        results = response.json()

        # Filter for synced lyrics
        synced_results = [r for r in results if r.get('syncedLyrics')]

        if not synced_results:
            print(f"No synced lyrics found for {artist} - {song_name}")
            return None

        # Pick the most relevant result (usually the first one)
        # We could refine this by exact string matching on artist/title if needed
        track = synced_results[0]
        print(
            f"Found lyrics for: {track.get('artistName')} - {track.get('trackName')}")

        return parse_lrc(track['syncedLyrics'])

    except Exception as e:
        print(f"Error fetching lyrics: {e}")
        return None


def search_lyrics(query):
    """
    Searches for synchronized lyrics from LRCLIB.net
    Returns list of track dicts with id, name, artist, album, duration, syncedLyrics
    """
    url = "https://lrclib.net/api/search"
    params = {"q": query}

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        results = response.json()

        # Filter for matched synced lyrics
        clean_results = []
        for r in results:
            if r.get('syncedLyrics'):
                clean_results.append({
                    'id': r.get('id'),
                    'name': r.get('trackName'),
                    'artist': r.get('artistName'),
                    'album': r.get('albumName'),
                    'duration': r.get('duration'),
                    'syncedLyrics': r.get('syncedLyrics'),
                    'plainLyrics': r.get('plainLyrics')
                })
        return clean_results

    except Exception as e:
        print(f"Error searching lyrics: {e}")
        return []


def get_lyrics_by_id(conn_id):
    """
    Fetches lyrics by LRCLIB ID
    """
    url = f"https://lrclib.net/api/get/{conn_id}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('syncedLyrics'):
            return parse_lrc(data['syncedLyrics'])
        return None
    except Exception as e:
        print(f"Error fetching lyrics by id: {e}")
        return None


def parse_lrc(lrc_string):
    """
    Parses LRC string into list of dicts with 'start' and 'text'.
    Supports standard [mm:ss.xx] format.
    """
    lines = []
    # Regex for [mm:ss.xx]
    regex = r"\[(\d+):(\d+\.?\d*)\](.*)"

    for line in lrc_string.split('\n'):
        line = line.strip()
        if not line:
            continue

        match = re.match(regex, line)
        if match:
            minutes = float(match.group(1))
            seconds = float(match.group(2))
            text = match.group(3).strip()

            # Skip empty lines if they don't convey musical pauses (optional decision)
            # But sometimes empty lines are useful for instrumental breaks.
            # For this generator, empty text might display nothing, which is fine.

            total_seconds = minutes * 60 + seconds
            lines.append({
                "start": total_seconds,
                "text": text
            })

    return lines


if __name__ == "__main__":
    # Test
    data = get_lyrics("Charli xcx", "Apple")
    if data:
        print(f"Fetched {len(data)} lines.")
        print(data[:3])
