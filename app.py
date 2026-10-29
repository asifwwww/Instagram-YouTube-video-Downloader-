"""Single-process, bounded job server. Run ONE uvicorn worker / ONE Render instance."""
import base64
from collections import deque
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import hmac
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from engine import normalize_url, UserError

BASE = Path(__file__).resolve().parent
ROOT = Path(os.getenv('DATA_DIR', '/tmp/media-workbench')).resolve()
TOKEN = os.getenv('APP_TOKEN', '')
PUBLIC = os.getenv('ALLOW_PUBLIC', 'false').lower() == 'true'
TTL = int(os.getenv('FILE_TTL_SECONDS', '1800'))
TIMEOUT = int(os.getenv('JOB_TIMEOUT_SECONDS', '300'))
MAX_FILE = int(os.getenv('MAX_FILE_MB', '80')) * 1024 * 1024
MAX_JOB = MAX_FILE * 3  # accommodates separate tracks + ffmpeg merge
MAX_DISK = int(os.getenv('MAX_DISK_MB', '350')) * 1024 * 1024
lock = threading.RLock()
work_lock = threading.Lock()
jobs = {}
rate = deque()
pool = ThreadPoolExecutor(max_workers=1)
stop = threading.Event()


def tree_size(path):
    total = 0
    for p in path.rglob('*'):
        try:
            if p.is_file():
                total += p.stat().st_size
        except FileNotFoundError:
            pass
    return total


def clean():
    now = time.time()
    with lock:
        for jid, job in list(jobs.items()):
            if job['status'] in ('done', 'error') and now - job['finished'] > TTL:
                shutil.rmtree(ROOT / jid, ignore_errors=True)
                del jobs[jid]


def janitor():
    while not stop.wait(30):
        clean()


@asynccontextmanager
async def lifespan(app):
    global pool
    pool = ThreadPoolExecutor(max_workers=1)
    jobs.clear()
    rate.clear()
    if not TOKEN and not PUBLIC:
        raise RuntimeError('Set APP_TOKEN (recommended), or explicitly set ALLOW_PUBLIC=true.')
    if not 5 <= MAX_FILE // (1024 * 1024) <= 250:
        raise RuntimeError('MAX_FILE_MB must be between 5 and 250.')
    if MAX_DISK < MAX_JOB:
        raise RuntimeError('MAX_DISK_MB must be at least 3 times MAX_FILE_MB.')
    # ROOT is app-exclusive temporary storage. Jobs do not survive restarts.
    ROOT.mkdir(parents=True, exist_ok=True)
    for p in ROOT.iterdir():
        if p.is_dir() and len(p.name) == 32 and all(c in '0123456789abcdef' for c in p.name):
            shutil.rmtree(p, ignore_errors=True)
    session_path = None
    if os.getenv('IG_SESSION_B64'):
        if not TOKEN or not os.getenv('IG_USERNAME'):
            raise RuntimeError('IG_SESSION_B64 requires APP_TOKEN and IG_USERNAME.')
        import tempfile
        try:
            raw = base64.b64decode(os.environ['IG_SESSION_B64'], validate=True)
            if not 1 <= len(raw) <= 1024 * 1024:
                raise ValueError()
        except Exception:
            raise RuntimeError('IG_SESSION_B64 is not a valid owner session base64 value.') from None
        fd, session_path = tempfile.mkstemp(prefix='media-ig-', suffix='.session')
        with os.fdopen(fd, 'wb') as session_file:
            session_file.write(raw)
        os.environ['IG_SESSION_FILE'] = session_path
    stop.clear()
    thread = threading.Thread(target=janitor, daemon=True)
    thread.start()
    yield
    stop.set()
    pool.shutdown(wait=True, cancel_futures=True)
    if session_path:
        Path(session_path).unlink(missing_ok=True)


app = FastAPI(title='Media Workbench', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount('/static', StaticFiles(directory=BASE / 'static'), name='static')


@app.middleware('http')
async def headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    return response


def authorized(request: Request):
    if TOKEN:
        supplied = request.headers.get('authorization', '')
        expected = 'Bearer ' + TOKEN
        if not hmac.compare_digest(supplied.encode(), expected.encode()):
            raise HTTPException(401, 'Enter the site access key configured by its owner.')
    elif not PUBLIC:
        raise HTTPException(503, 'Site access is not configured.')


class JobInput(BaseModel):
    url: str = Field(min_length=10, max_length=2048)
    action: Literal['metadata', 'video', 'images', 'transcript', 'audio_transcript', 'seo']
    language: Literal['en', 'ur', 'hi', 'ar'] = 'en'
    rights_confirmed: bool = False


def set_error(jid, error):
    with lock:
        jobs[jid].update(status='error', error=error, finished=time.time())
    shutil.rmtree(ROOT / jid, ignore_errors=True)


def kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def process_job(jid, payload):
    folder = ROOT / jid
    proc = None
    try:
        with work_lock:
            with lock:
                jobs[jid]['status'] = 'running'
            folder.mkdir(mode=0o700)
            payload_path = folder / 'input.json'
            payload_path.write_text(json.dumps(payload), encoding='utf-8')
            proc = subprocess.Popen([sys.executable, str(BASE / 'engine.py'), str(payload_path), str(folder)],
                start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            deadline = time.monotonic() + TIMEOUT
            while proc.poll() is None:
                if time.monotonic() > deadline:
                    kill_group(proc)
                    set_error(jid, 'Job timed out. Try a shorter video or retry later.')
                    return
                if tree_size(folder) > MAX_JOB or tree_size(ROOT) > MAX_DISK:
                    kill_group(proc)
                    set_error(jid, 'Temporary storage limit reached. Try a smaller file or wait for older jobs to expire.')
                    return
                time.sleep(0.5)
            output = folder / 'result.json'
            if not output.exists():
                set_error(jid, 'Worker stopped unexpectedly. Try a smaller video.')
                return
            data = json.loads(output.read_text(encoding='utf-8'))
            if not data.get('ok'):
                set_error(jid, data.get('error', 'Extraction failed.'))
                return
            result = data['result']
            output.unlink(missing_ok=True)
            with lock:
                jobs[jid].update(status='done', result=result, finished=time.time())
    except Exception:
        if proc and proc.poll() is None:
            kill_group(proc)
        set_error(jid, 'Job failed unexpectedly. Check deployment configuration and try again.')


@app.get('/')
def index():
    return FileResponse(BASE / 'static' / 'index.html')


@app.get('/healthz')
def health():
    return {'status': 'ok'}


@app.get('/api/config')
def config():
    return {'token_required': bool(TOKEN), 'ai_enabled': bool(os.getenv('OPENAI_API_KEY')),
            'stories_enabled': bool(TOKEN and os.getenv('IG_USERNAME') and os.getenv('IG_SESSION_FILE')),
            'max_file_mb': MAX_FILE // (1024 * 1024), 'max_duration_seconds': int(os.getenv('MAX_DURATION_SECONDS', '900')),
            'ttl_seconds': TTL}


@app.post('/api/jobs', dependencies=[Depends(authorized)], status_code=202)
def create_job(payload: JobInput):
    if not payload.rights_confirmed:
        raise HTTPException(400, 'Confirm ownership or permission before processing this content.')
    try:
        _, normalized = normalize_url(payload.url)
    except UserError as e:
        raise HTTPException(400, str(e))
    if payload.action in ('seo', 'audio_transcript') and not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(400, 'This optional feature needs the owner’s OpenAI API key and may incur charges.')
    clean()
    now = time.time()
    with lock:
        while rate and now - rate[0] > 60:
            rate.popleft()
        if len(rate) >= 12:
            raise HTTPException(429, 'Site-wide request limit reached. Wait one minute.')
        if any(j['status'] in ('queued', 'running') for j in jobs.values()):
            raise HTTPException(429, 'One job is already running. Wait for it to finish.')
        if len(jobs) >= 20 or tree_size(ROOT) > MAX_DISK - MAX_JOB:
            raise HTTPException(429, 'Temporary storage is busy. Download existing results and wait for expiry.')
        rate.append(now)
        jid = secrets.token_hex(16)
        jobs[jid] = {'status': 'queued', 'created': now}
        body = payload.model_dump()
        body['url'] = normalized
        pool.submit(process_job, jid, body)
    return {'id': jid, 'status': 'queued'}


@app.get('/api/jobs/{jid}', dependencies=[Depends(authorized)])
def status(jid: str):
    clean()
    with lock:
        if jid not in jobs:
            raise HTTPException(404, 'Job expired or server restarted. Submit the link again.')
        job = jobs[jid]
        result = {'id': jid, **job}
        return result


@app.get('/api/files/{jid}/{filename}', dependencies=[Depends(authorized)])
def download(jid: str, filename: str):
    clean()
    with lock:
        job = jobs.get(jid)
        if not job or job['status'] != 'done':
            raise HTTPException(404, 'File unavailable or expired.')
        allowed = {f['name'] for f in job['result']['files']}
        if filename not in allowed or Path(filename).name != filename:
            raise HTTPException(404, 'File not found.')
        path = ROOT / jid / filename
        if not path.is_file():
            raise HTTPException(404, 'File expired.')
    return FileResponse(path, filename=filename, headers={'Cache-Control': 'no-store'})
