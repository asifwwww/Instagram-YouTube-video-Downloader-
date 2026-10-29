import os
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

app = Flask(__name__)
CORS(app)

def get_yt_video_id(url):
    pattern = r'(?:v=|\/|youtu\.be\/|shorts\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def clean_url(url):
    # Threads ya doosre platforms ke tracking parameters aur short links ko resolve karna
    if "threads.net" in url or "threads.com" in url:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(url, headers=headers, allow_redirects=True, timeout=5)
            url = resp.url.split('?')[0]
        except Exception:
            url = url.split('?')[0]
    else:
        url = url.split('?xmt=')[0].split('&')[0]
    return url

@app.route('/')
def home():
    return jsonify({"status": "API is live and working!"})

@app.route('/api/fetch-info', methods=['POST'])
def fetch_info():
    data = request.json
    raw_url = data.get('url')
    
    if not raw_url:
        return jsonify({"success": False, "error": "URL required hai"}), 400

    url = clean_url(raw_url)

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best',
        'noplaylist': True,
        'socket_timeout': 20,
        'extractor_args': {
            'youtube': {'player_client': ['android', 'web']}
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = []
            if 'formats' in info:
                for f in info.get('formats', []):
                    if f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
                        formats.append({
                            'format_id': f.get('format_id'),
                            'resolution': f.get('format_note') or f.get('resolution') or f"{f.get('height')}p",
                            'url': f.get('url')
                        })

            response_data = {
                "title": info.get('title') or "Media Title",
                "description": info.get('description') or "",
                "thumbnail": info.get('thumbnail') or "",
                "uploader": info.get('uploader') or info.get('uploader_id') or "Unknown",
                "duration": info.get('duration'),
                "view_count": info.get('view_count'),
                "tags": info.get('tags', []),
                "direct_download_url": info.get('url'),
                "formats": formats[-5:] if formats else []
            }
            return jsonify({"success": True, "data": response_data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200

@app.route('/api/transcript', methods=['POST'])
def get_transcript():
    data = request.json
    url = data.get('url')
    
    video_id = get_yt_video_id(url) if url else None
    if not video_id:
        return jsonify({"success": False, "error": "Valid YouTube Video URL required hai"}), 400

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([item['text'] for item in transcript_list])
        return jsonify({"success": True, "transcript": full_text})
    except TranscriptsDisabled:
        return jsonify({"success": False, "error": "Is video par transcript/subtitles disabled hain."}), 200
    except NoTranscriptFound:
        return jsonify({"success": False, "error": "Is video ki koi transcript nahi mili."}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
