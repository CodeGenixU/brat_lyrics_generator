import argparse
import json
import math
import os
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, ImageClip, CompositeVideoClip, ColorClip
import numpy as np


def get_wrapped_lines(words, font, max_width):
    """
    Splits a list of words into lines that fit within max_width.
    Returns a list of lines, where each line is a list of word strings.
    """
    lines = []
    current_line = []

    # We measure space width for calculation
    space_width = font.getbbox(" ")[2]
    current_width = 0

    for word_text in words:
        word_width = font.getbbox(word_text)[2]

        if not current_line:
            current_line.append(word_text)
            current_width = word_width
        else:
            # Check if adding this word (plus space) exceeds max_width
            new_width = current_width + space_width + word_width
            if new_width <= max_width:
                current_line.append(word_text)
                current_width = new_width
            else:
                lines.append(current_line)
                current_line = [word_text]
                current_width = word_width

    if current_line:
        lines.append(current_line)

    return lines


def calculate_layout_metrics(lines, font):
    """
    Calculates total width and height for a given set of lines and font.
    Returns (width, height, line_heights, line_spacing)
    """
    max_line_width = 0
    total_height = 0
    line_heights = []

    bbox_ref = font.getbbox("Ay")
    base_line_height = bbox_ref[3] - bbox_ref[1]

    line_spacing = 10

    for line_words in lines:
        if not line_words:
            continue
        line_str = " ".join(line_words)
        w = font.getbbox(line_str)[2]
        max_line_width = max(max_line_width, w)
        line_heights.append(base_line_height)
        total_height += base_line_height

    total_height += line_spacing * (len(lines) - 1) if lines else 0

    return max_line_width, total_height, line_heights, line_spacing


def get_optimal_font_size(words, max_size, min_font=20, max_font=400):
    """
    Binary search for font size.
    Wraps text at each size and checks against max_size.
    """
    font_path = "arial.ttf"
    target_width = max_size[0] - 100  # Padding horizontal
    # This is already the constrained height passing in
    target_height = max_size[1]

    def check_fit(size):
        try:
            font = ImageFont.truetype(font_path, size)
        except:
            font = ImageFont.load_default()

        lines = get_wrapped_lines(words, font, target_width)
        w, h, _, _ = calculate_layout_metrics(lines, font)
        return w <= target_width and h <= target_height

    low, high = min_font, max_font
    best_size = min_font

    while low <= high:
        mid = (low + high) // 2
        if check_fit(mid):
            best_size = mid
            low = mid + 1
        else:
            high = mid - 1

    return best_size


def calculate_word_positions(lines, font_size, size):
    """
    Calculates absolute positions with Justified Alignment.
    """
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()

    _, total_text_height, line_heights, line_spacing = calculate_layout_metrics(
        lines, font)

    MAX_WIDTH = size[0] - 100  # Match padding used in sizing
    start_x = 50  # Padding left

    # FIXED TOP ALIGNMENT (User Request)
    # Start at 20% height
    start_y = int(size[1] * 0.2)
    current_y = start_y
    space_width = font.getbbox(" ")[2]

    target_width = MAX_WIDTH
    word_positions = []

    for i, line_words in enumerate(lines):
        # Determine Alignment
        is_last_line = (i == len(lines) - 1)

        # Calculate natural width (with normal spaces) to check fullness
        sum_word_w = sum(font.getbbox(w)[2] for w in line_words)
        normal_gap_w = (len(line_words) - 1) * space_width
        natural_width = sum_word_w + normal_gap_w

        # Threshold: If line is >85% full, justify it even if last line
        # to avoid jump when wrapping.
        is_full_enough = (natural_width / target_width) > 0.85

        should_left_align = (
            is_last_line and not is_full_enough) or len(line_words) == 1

        if should_left_align:
            # Left Align
            curr_x = start_x
            for w in line_words:
                w_w = font.getbbox(w)[2]
                word_positions.append({'text': w, 'x': curr_x, 'y': current_y})
                curr_x += w_w + space_width
        else:
            # Justify Align
            available_space = target_width - sum_word_w

            if len(line_words) > 1:
                gap = available_space / (len(line_words) - 1)
            else:
                gap = 0

            curr_x = (size[0] - target_width) // 2  # Centered block

            for index, w in enumerate(line_words):
                w_w = font.getbbox(w)[2]
                word_positions.append(
                    {'text': w, 'x': int(curr_x), 'y': current_y})
                curr_x += w_w + gap

        current_y += line_heights[i] + line_spacing

    return word_positions, font


def create_text_image(text, size=(1080, 1920), bg_color=(255, 255, 255), text_color=(0, 0, 0), font_path="arial.ttf", font_size=100):
    # Legacy function for fallback, mostly unused now
    return np.array(Image.new('RGB', size, color=bg_color))


def create_frame(word_positions, visible_count, size, bg_color, text_color, font, lofi_factor=1):
    img = Image.new('RGB', size, color=bg_color)
    draw = ImageDraw.Draw(img)

    for i in range(min(visible_count, len(word_positions))):
        item = word_positions[i]
        draw.text((item['x'], item['y']), item['text'],
                  font=font, fill=text_color)

    if lofi_factor > 1:
        small_size = (max(1, size[0] // lofi_factor),
                      max(1, size[1] // lofi_factor))
        img = img.resize(small_size, Image.BILINEAR)
        img = img.resize(size, Image.NEAREST)

    return np.array(img)


def generate_video(audio_path, output_path, lyrics_path=None, bg_color_hex="#FFFFFF", max_font_size=400, lofi_factor=1):
    VIDEO_SIZE = (1080, 1920)
    # Define effective text area
    # 20% top padding, 20% bottom padding -> 60% height usable
    MAX_TEXT_HEIGHT = VIDEO_SIZE[1] * 0.6

    bg_color = tuple(int(bg_color_hex.lstrip(
        '#')[i:i+2], 16) for i in (0, 2, 4))
    text_color = (0, 0, 0)

    # Load audio early to get duration
    try:
        audio = AudioFileClip(audio_path)
    except Exception as e:
        print(f"Error loading audio: {e}")
        return

    raw_lyrics = []

    if lyrics_path:
        try:
            with open(lyrics_path, 'r', encoding='utf-8') as f:
                raw_lyrics = json.load(f)
        except Exception as e:
            print(f"Error loading lyrics file: {e}")
            return
    else:
        print("Error: Must provide --lyrics file.")
        return

    clips = []

    # Pre-process: Convert Line-based input to Word-based segments
    # Input: [ {"start": 0.0, "text": "Line 1"}, {"start": 3.0, "text": "Line 2"} ]
    processed_segments = []

    for i, line_item in enumerate(raw_lyrics):
        start_time = float(line_item.get('start', 0.0))
        text = line_item.get('text', "")

        # Determine End Time
        if i < len(raw_lyrics) - 1:
            next_start = float(raw_lyrics[i+1].get('start', 0.0))
            end_time = next_start
        else:
            end_time = audio.duration

        duration = end_time - start_time
        if duration <= 0:
            duration = 0.5  # Fallback

        words = text.split()
        if not words:
            continue

        time_per_word = duration / len(words)

        segment_words = []
        for j, w in enumerate(words):
            w_time = start_time + (j * time_per_word)
            segment_words.append({
                "time": w_time,
                "text": w
            })

        processed_segments.append({"words": segment_words})

    # Main Loop (using processed segments)
    for segment_idx, segment in enumerate(processed_segments):
        words_data = segment.get('words', [])
        if not words_data:
            continue

        words_data.sort(key=lambda x: x['time'])

        # We now calculate layout PER FRAME (per word addition)

        for i, word_item in enumerate(words_data):
            # 1. Get currently visible words
            current_visible_data = words_data[:i+1]
            current_words_text = [w['text'] for w in current_visible_data]

            # 2. Optimal Font Size for CURRENT text
            # We pass (WIDTH, MAX_TEXT_HEIGHT) to constrain logic
            best_font_size = get_optimal_font_size(
                current_words_text, (VIDEO_SIZE[0], MAX_TEXT_HEIGHT), max_font=max_font_size)

            try:
                font = ImageFont.truetype("arial.ttf", best_font_size)
            except:
                font = ImageFont.load_default()

            # 3. Calculate Layout for CURRENT text
            lines = get_wrapped_lines(
                current_words_text, font, VIDEO_SIZE[0] - 100)
            word_positions, _ = calculate_word_positions(
                lines, best_font_size, VIDEO_SIZE)

            # Timing logic
            start_time = word_item['time']
            if i < len(words_data) - 1:
                end_time = words_data[i+1]['time']
                duration = end_time - start_time
            else:
                if segment_idx < len(processed_segments) - 1:
                    next_seg = processed_segments[segment_idx+1]
                    if next_seg.get('words'):
                        end_time = next_seg['words'][0]['time']
                    else:
                        end_time = audio.duration
                else:
                    end_time = audio.duration

            if duration <= 0:
                duration = 0.05

            # Draw frame
            img_array = create_frame(word_positions, len(
                word_positions), VIDEO_SIZE, bg_color, text_color, font, lofi_factor=lofi_factor)
            clip = ImageClip(img_array).set_duration(
                duration).set_start(start_time)
            clips.append(clip)

    # Create Background Clip
    background_clip = ColorClip(
        size=VIDEO_SIZE, color=bg_color).set_duration(audio.duration)

    final_video = CompositeVideoClip(
        [background_clip] + clips, size=VIDEO_SIZE)
    final_video = final_video.set_audio(audio)
    final_video = final_video.set_duration(audio.duration)

    final_video.write_videofile(
        output_path, fps=24, codec='libx264', audio_codec='aac')
    print(f"Video saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Brat Lyrics Video Generator")
    parser.add_argument("--audio", required=True,
                        help="Path to the audio file")
    parser.add_argument("--lyrics", required=True,
                        help="Path to the lyrics JSON file")
    parser.add_argument("--output", default="output.mp4",
                        help="Path to the output video file")
    parser.add_argument("--bgcolor", default="#FFFFFF",
                        help="Hex code for background color")
    parser.add_argument("--fontsize", type=int, default=400,
                        help="Maximum font size (starting size)")
    parser.add_argument("--lofi", type=int, default=1,
                        help="Lo-Fi factor (1=None, 5=Standard, 10=Extra)")

    args = parser.parse_args()

    generate_video(args.audio, args.output, lyrics_path=args.lyrics,
                   bg_color_hex=args.bgcolor, max_font_size=args.fontsize, lofi_factor=args.lofi)
