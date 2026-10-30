import os
import re
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

def clean_url(url):
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
    return jsonify({"status": "Social Media Downloader API is live!"})

@app.route('/api/fetch-info', methods=['POST'])
def fetch_info():
    data = request.json
    raw_url = data.get('url')
    
    if not raw_url:
        return jsonify({"success": False, "error": "URL required hai"}), 400

    url = clean_url(raw_url)

    # Social platforms ke liye optimized headers aur options
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best',
        'noplaylist': True,
        'socket_timeout': 20,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
                "title": info.get('title') or info.get('description') or "Media Download",
                "description": info.get('description') or "",
                "thumbnail": info.get('thumbnail') or "",
                "uploader": info.get('uploader') or info.get('uploader_id') or "Creator",
                "duration": info.get('duration'),
                "direct_download_url": info.get('url'),
                "formats": formats[-5:] if formats else []
            }
            return jsonify({"success": True, "data": response_data})

    except Exception as e:
        # Hamesha valid JSON error return karega taake unreadable response ka error na aaye
        return jsonify({"success": False, "error": f"Extraction Error: {str(e)}"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
