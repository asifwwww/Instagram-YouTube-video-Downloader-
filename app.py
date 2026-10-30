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
            headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15"}
            resp = requests.get(url, headers=headers, allow_redirects=True, timeout=5)
            url = resp.url.split('?')[0]
        except Exception:
            url = url.split('?')[0]
    else:
        url = url.split('?xmt=')[0].split('&')[0]
    return url

@app.route('/')
def home():
    return jsonify({"status": "Social Downloader API is live!"})

@app.route('/api/fetch-info', methods=['POST'])
def fetch_info():
    data = request.json
    raw_url = data.get('url')
    
    if not raw_url:
        return jsonify({"success": False, "error": "URL required hai"}), 200

    url = clean_url(raw_url)

    # Multi-client fallback options for yt-dlp to bypass blocks
    ydl_opts_list = [
        {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp4]/best',
            'noplaylist': True,
            'socket_timeout': 15,
            'extractor_args': {'instagram': {'api': 'graphql'}}
        },
        {
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'noplaylist': True,
            'socket_timeout': 15,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        }
    ]

    info = None
    last_error = ""

    for ydl_opts in ydl_opts_list:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    break
        except Exception as e:
            last_error = str(e)
            continue

    if not info:
        return jsonify({"success": False, "error": f"Extraction failed: Platform block kar raha hai. Dobara koshish karein."}), 200

    try:
        formats = []
        if 'formats' in info:
            for f in info.get('formats', []):
                if f.get('url') and f.get('vcodec') != 'none':
                    formats.append({
                        'format_id': f.get('format_id'),
                        'resolution': f.get('format_note') or f.get('resolution') or f"{f.get('height')}p" if f.get('height') else 'HD',
                        'url': f.get('url')
                    })

        response_data = {
            "title": info.get('title') or info.get('description') or "Social Media Media",
            "description": info.get('description') or "",
            "thumbnail": info.get('thumbnail') or "",
            "uploader": info.get('uploader') or info.get('uploader_id') or "Creator",
            "duration": info.get('duration'),
            "direct_download_url": info.get('url') or (formats[0]['url'] if formats else ""),
            "formats": formats[-5:] if formats else []
        }
        return jsonify({"success": True, "data": response_data})

    except Exception as e:
        return jsonify({"success": False, "error": f"Processing error: {str(e)}"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
