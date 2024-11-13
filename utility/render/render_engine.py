import os
import tempfile
import platform
import subprocess
import logging
from moviepy.editor import (AudioFileClip, CompositeVideoClip, TextClip, VideoFileClip, concatenate_videoclips)
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import mmap

def download_file(url, filename):
    try:
        with open(filename, 'wb') as f:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            f.write(response.content)
        return True
    except requests.RequestException as e:
        logging.error(f"Error downloading file from {url}: {str(e)}")
        return False

def search_program(program_name):
    try: 
        search_cmd = "where" if platform.system() == "Windows" else "which"
        return subprocess.check_output([search_cmd, program_name]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_program_path(program_name):
    program_path = search_program(program_name)
    return program_path

def create_video_clip(video_url, t1, t2):
    video_filename = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    if download_file(video_url, video_filename):
        try:
            video_clip = VideoFileClip(video_filename).subclip(0, t2-t1)
            video_clip = video_clip.set_start(t1).set_end(t2)
            return video_clip
        except Exception as e:
            logging.error(f"Error processing video clip: {str(e)}")
    return None

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server):
    OUTPUT_FILE_NAME = "rendered_video.mp4"
    magick_path = get_program_path("magick")
    logging.info(f"ImageMagick path: {magick_path}")
    if magick_path:
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
    else:
        os.environ['IMAGEMAGICK_BINARY'] = '/usr/bin/convert'
    
    visual_clips = []
    
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(create_video_clip, video_url, t1, t2) for (t1, t2), video_url in background_video_data if video_url]
        for future in as_completed(futures):
            video_clip = future.result()
            if video_clip:
                visual_clips.append(video_clip)
    
    try:
        audio_clip = AudioFileClip(audio_file_path)
    except Exception as e:
        logging.error(f"Error loading audio file: {str(e)}")
        return None

    for (t1, t2), text in timed_captions:
        try:
            text_clip = TextClip(txt=text, fontsize=50, color="white", stroke_width=2, stroke_color="black", method='caption', size=(1920, 1080))
            text_clip = text_clip.set_start(t1).set_end(t2).set_position(('center', 'bottom'))
            visual_clips.append(text_clip)
        except Exception as e:
            logging.error(f"Error creating text clip: {str(e)}")

    try:
        video = CompositeVideoClip(visual_clips, size=(1920, 1080))
        video = video.set_audio(audio_clip)
        video = video.set_duration(audio_clip.duration)

        with open(OUTPUT_FILE_NAME, 'wb') as f:
            f.write(b'\0' * (1024 * 1024 * 100))  # Pre-allocate 100MB
        with open(OUTPUT_FILE_NAME, 'r+b') as f:
            mm = mmap.mmap(f.fileno(), 0)
            video.write_videofile(mm, codec='libx264', audio_codec='aac', fps=30, threads=4, logger=None)
    except Exception as e:
        logging.error(f"Error rendering final video: {str(e)}")
        return None
    
    # Clean up downloaded files
    for clip in visual_clips:
        if isinstance(clip, VideoFileClip) and os.path.exists(clip.filename):
            os.remove(clip.filename)

    return OUTPUT_FILE_NAME

def combine_video_segments(segment_videos):
    try:
        clips = [VideoFileClip(video) for video in segment_videos]
        final_clip = concatenate_videoclips(clips)
        final_clip.write_videofile("final_video.mp4", codec='libx264', audio_codec='aac', threads=4, logger=None)
        return "final_video.mp4"
    except Exception as e:
        logging.error(f"Error combining video segments: {str(e)}")
        return None