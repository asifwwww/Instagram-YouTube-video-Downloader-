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

def is_direct_playable(f):
    """Prefer progressive HTTP/HTTPS progressive files that open easily in browser (CDN style)."""
    url = (f.get('url') or '')
    protocol = (f.get('protocol') or '').lower()
    ext = (f.get('ext') or '').lower()
    if not url.startswith('http'):
        return False
    # Skip pure HLS/DASH manifests – browsers often cannot open them as simple video
    if 'm3u8' in url.lower() or protocol in ('m3u8', 'm3u8_native', 'http_dash_segments', 'dash'):
        return False
    if ext in ('m3u8', 'mpd'):
        return False
    return True

def has_video(f):
    vcodec = (f.get('vcodec') or 'none').lower()
    return vcodec not in ('none', 'null') and f.get('height')

def has_audio_track(f):
    acodec = (f.get('acodec') or 'none').lower()
    return acodec not in ('none', 'null')

@app.route('/')
def home():
    return jsonify({"status": "Social Downloader API is live!"})

@app.route('/api/fetch-info', methods=['POST'])
def fetch_info():
    data = request.json or {}
    raw_url = data.get('url')

    if not raw_url:
        return jsonify({"success": False, "error": "URL required hai"}), 200

    url = clean_url(raw_url)

    # Flexible options – Twitter/X ke liye graphql + syndication, better combined formats
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[acodec!=none][vcodec!=none]/best[height<=1080][acodec!=none]/bestvideo+bestaudio/best',
        'noplaylist': True,
        'socket_timeout': 25,
        'extractor_args': {
            'twitter': {'api': ['graphql', 'syndication']},
            'tiktok': {'api_hostname': 'api22-normal-c-useast1a.tiktokv.com'},
        },
        # Prefer formats that browsers can open directly
        'prefer_free_formats': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            video_formats = []
            audio_formats = []
            seen_urls = set()

            raw_formats = info.get('formats') or []

            # Sort: prefer higher height, then those with audio, then direct playable
            def sort_key(f):
                h = f.get('height') or 0
                a = 1 if has_audio_track(f) else 0
                d = 1 if is_direct_playable(f) else 0
                return (d, a, h)

            sorted_fmts = sorted(raw_formats, key=sort_key, reverse=True)

            for f in sorted_fmts:
                u = f.get('url')
                if not u or u in seen_urls:
                    continue
                seen_urls.add(u)

                height = f.get('height')
                width = f.get('width')
                ext = (f.get('ext') or 'mp4').lower()
                filesize = f.get('filesize') or f.get('filesize_approx')
                acodec = (f.get('acodec') or 'none').lower()
                vcodec = (f.get('vcodec') or 'none').lower()
                has_a = has_audio_track(f)
                has_v = has_video(f)

                resolution = (
                    f.get('format_note')
                    or f.get('resolution')
                    or (f"{height}p" if height else None)
                    or "HD"
                )

                entry = {
                    'format_id': f.get('format_id'),
                    'resolution': resolution,
                    'url': u,
                    'height': height,
                    'width': width,
                    'ext': e
... 
