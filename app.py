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

    # Instagram aur baaki platforms ke liye browser impersonation options
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best',
        'noplaylist': True,
        'socket_timeout': 25,
        'impersonate': 'chrome',  # Instagram bot detection bypass karne ke liye zaroori hai
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
        return jsonify({"success": False, "error": f"Error: {str(e)}"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
