import os
import re
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

@app.route('/')
def home():
    return jsonify({"status": "API is live and working!"})

# Video & Reel Downloader + Metadata Endpoint
@app.route('/api/fetch-info', methods=['POST'])
def fetch_info():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "URL required hai"}), 400

    # YouTube aur Instagram ke liye behtar options
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = []
            if 'formats' in info:
                for f in info.get('formats', []):
                    # Sirf wese formats lein jisme video aur audio dono hon ya achi quality ho
                    if f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
                        formats.append({
                            'format_id': f.get('format_id'),
                            'resolution': f.get('format_note') or f.get('resolution') or f"{f.get('height')}p",
                            'url': f.get('url')
                        })

            response_data = {
                "title": info.get('title'),
                "description": info.get('description'),
                "thumbnail": info.get('thumbnail'),
                "uploader": info.get('uploader') or info.get('uploader_id'),
                "duration": info.get('duration'),
                "view_count": info.get('view_count'),
                "tags": info.get('tags', []),
                "direct_download_url": info.get('url'),
                "formats": formats[-5:] if formats else [] # Last top formats
            }
            return jsonify({"success": True, "data": response_data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# YouTube Transcript Generator Endpoint
@app.route('/api/transcript', methods=['POST'])
def get_transcript():
    data = request.json
    url = data.get('url')
    
    video_id = get_yt_video_id(url) if url else None
    if not video_id:
        return jsonify({"error": "Valid YouTube Video URL required hai"}), 400

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_text = " ".join([item['text'] for item in transcript_list])
        return jsonify({"success": True, "transcript": full_text})
    except TranscriptsDisabled:
        return jsonify({"success": False, "error": "Is video par transcript/subtitles disabled hain."}), 400
    except NoTranscriptFound:
        return jsonify({"success": False, "error": "Is video ki koi transcript nahi mili."}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
