# Media Workbench — GitHub + Render

YouTube aur Instagram ke permitted media, metadata aur transcripts ke liye responsive website. Python/FastAPI backend, plain HTML/CSS/JS frontend, yt-dlp, FFmpeg, Node.js aur Instaloader. Frontend aur backend **ek hi Render Web Service** mein chaltay hain. React, separate database ya separate frontend hosting ki zaroorat nahin.

## Pehle important baat

Yeh complete runnable application source hai, lekin **har public link ka successful download guaranteed nahin**. YouTube/Instagram ki policies, login requirements, region blocks, datacenter-IP blocks, expired stories aur extractor changes is app ke control se bahar hain. App failure ko clearly show karti hai; fake success/download links nahin banati. Sirf apna ya permission wala content process karein. Copyright, privacy aur platform terms follow karein. DRM, paywall, private-account aur login bypass included nahin.

## 1. Features aur actual conditions

- **YouTube video / Shorts:** available formats se MP4 preferred, maximum 720p; format fallback kisi aur supported container mein ho sakta hai. Video ke saath audio merge ke liye FFmpeg included hai. Default known duration <= 15 minutes; maximum output file 80 MB. No playlist/channel download. Public source ka blocked hona possible hai.
- **YouTube thumbnail:** extractor ka best available thumbnail original supported image format mein download hota hai. Har resolution ka separate selector nahin hai.
- **YouTube source metadata:** title, description, creator, duration, date, available views/likes/tags; JSON export. Missing platform fields invent nahin kiye jatay.
- **YouTube captions transcript:** selected language ki available manual/automatic captions se TXT + JSON with timestamps. No paid AI key needed. Captions absent hon to clear error. Automatic captions imperfect ho sakti hain.
- **YouTube audio transcript:** captions unavailable hon to optional OpenAI audio transcription. Paid API key required; 15-minute duration guard applies.
- **Instagram post / Reel / carousel:** public, accessible post ka video aur images download; carousel mein maximum first 20 media items. Stories ke ilawa anonymous extractor use hota hai; Instagram anonymous requests ko frequently block karta hai.
- **Instagram story video / image:** specific active story URL, trusted operator ki authorized session, aur password-protected site required. Sirf public profile; private profile deliberately refused. Expired/unavailable story recover nahin hoti. Story text/caption OCR included nahin.
- **Instagram source metadata:** caption/description, creator, timestamp, source URL, available hashtags; JSON export.
- **Instagram transcript:** video ki speech ka optional paid OpenAI ASR. Instagram ka generic public transcript API nahin hai. Photo ka audio transcript nahin hota.
- **AI metadata generator:** YouTube ya Instagram metadata se new title, description, tags, hashtags; optional paid OpenAI key required. Yeh video dekh kar verified facts generate nahin karta. Extract metadata aur Generate metadata separate actions hain.
- **Languages:** English, Urdu, Hindi, Arabic. Caption tracks must be available in the chosen language. Urdu ASR output Roman Urdu hona guaranteed nahin.
- **UI:** mobile + desktop; light/dark system theme; access key; progress polling; clear errors; result copy; file download.

## 2. Project files

```text
media-workbench/
├── app.py                  # protected API, bounded background jobs, cleanup
├── engine.py               # isolated media/caption/AI extraction worker
├── static/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
│   ├── test_engine.py      # offline unittest tests
│   └── test_api.py         # API tests, requires dev dependencies
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile              # Python + FFmpeg + Node 22
├── render.yaml             # optional Render Blueprint
├── .env.example
├── .github/workflows/tests.yml
├── VALIDATION.md
└── README.md
```

## 3. GitHub par upload — browser method

1. ZIP extract karein. Andar ke **project files** upload karne hain, ZIP file nahin.
2. GitHub account mein sign in -> **New repository** -> name `media-workbench` -> preferably **Private** -> **Create repository**.
3. **Add file -> Upload files** kholein. Project ke files/folders repository root mein upload karein. Root par `Dockerfile`, `app.py`, `requirements.txt` nazar aane chahiye, extra nested folder ke andar nahin.
4. **Commit changes** karein.
5. Hidden files (`.gitignore`, `.dockerignore`, `.github/`) browser se miss ho saktay hain. Reliable upload ke liye neeche Git method use karein. `.env.example` safe sample hai; real `.env`, API keys, cookies ya session file kabhi upload na karein.

### Git method — recommended

Git installed ho; terminal ko extracted `media-workbench` folder mein open karein:

```bash
git init
git add .
git commit -m "Add Media Workbench"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/media-workbench.git
git push -u origin main
```

`YOUR_USERNAME` replace karein. Agar repository already initialized hai to appropriate existing remote/branch use karein. GitHub password ki bajaye GitHub Desktop, browser authentication ya approved Git credential flow use karein. Secrets source code mein na likhein.

## 4. Render par deploy — easiest manual method

1. Render account -> **New + -> Web Service**.
2. GitHub connect karein; private repository ki permission allow karke `media-workbench` select karein.
3. Name apni marzi ka, branch `main`, root directory blank (agar files root mein upload ki hain).
4. Runtime/language **Docker** select karein. Dockerfile path `./Dockerfile`.
5. Region apne users ke qareeb. Small **paid** instance recommended for media/FFmpeg. Current plan price Render dashboard mein check karein. Free instance available ho to testing ke liye use kar saktay hain; sleep/resource/network restrictions expect karein.
6. **Environment** mein yeh set karein:

```text
APP_TOKEN=<long-random-secret>
ALLOW_PUBLIC=false
MAX_FILE_MB=80
MAX_DURATION_SECONDS=900
MAX_DISK_MB=350
FILE_TTL_SECONDS=1800
JOB_TIMEOUT_SECONDS=300
```

`<long-random-secret>` literal mat rakhna! Apna random secret banayein, misal ke taur par local command:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

7. Optional AI features ke liye Render environment mein add karein:

```text
OPENAI_API_KEY=<your-server-side-key>
AI_MODEL=gpt-4o-mini
ASR_MODEL=whisper-1
```

Provider account mein billing/budget set karein. Model availability badal sakti hai, is liye apne account ke supported model se variable update kar saktay hain. **API key browser JS, GitHub ya site access-key field mein nahin dalni.**
8. Health check path `/healthz` set karein. **Deploy Web Service** dabayein.
9. Build Dockerfile se dependencies install karegi. Start/build commands manually fill karne ki zaroorat nahin. Docker command `$PORT` par `0.0.0.0` bind karta hai.
10. Deployment Live hone par Render ka HTTPS URL kholein. **Site access key** mein `APP_TOKEN` ki value dalein. Content ownership/permission checkbox tick karein. Apni short public video se pehle **Extract metadata** try karein.
11. Update ke liye code GitHub par push karein, phir Render auto-deploy ya **Manual Deploy**. Dependency upgrade ke liye **Clear build cache & deploy** option available ho to use karein.

### Render Blueprint alternative

Render -> **New + -> Blueprint** -> repository select -> `render.yaml` detect hone dein -> plan/cost review -> apply. Included blueprint `starter` paid plan request karta hai; billing samajh kar apply karein. `APP_TOKEN` Render generate karega; dashboard Environment se copy karke website mein enter karein. Optional OpenAI/story environment variables manually add karein.

**Main ne aap ke GitHub/Render accounts mein repository ya live deployment create nahin ki. Yeh steps aap run karenge.**

## 5. Local run

### Docker — recommended, all runtimes included

Docker Desktop / Docker Engine installed ho:

```bash
cp .env.example .env
# .env edit karke APP_TOKEN replace karein; optional AI key add karein.
docker build -t media-workbench .
docker run --rm --env-file .env -p 10000:10000 media-workbench
```

Windows PowerShell mein first command: `Copy-Item .env.example .env`.
Browser: `http://localhost:10000`.

### Without Docker

Python 3.12+, Node.js 22+ aur FFmpeg/ffprobe install karein. Node 22 YouTube ke modern JS challenge solver ke liye included hai; `yt-dlp[default]` matching EJS dependency install karta hai.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux/macOS:

```bash
export APP_TOKEN='YOUR_LONG_RANDOM_SECRET'
# optional: export OPENAI_API_KEY='YOUR_KEY'
uvicorn app:app --host 0.0.0.0 --port 10000 --workers 1 --no-proxy-headers
```

Windows PowerShell:

```powershell
$env:APP_TOKEN='YOUR_LONG_RANDOM_SECRET'
uvicorn app:app --host 0.0.0.0 --port 10000 --workers 1 --no-proxy-headers
```

`.env` automatically load nahin hoti; Docker `--env-file` load karta hai. Local uvicorn ke liye shell variables set karein.

## 6. Instagram stories — optional authorized setup

Instagram story retrieval ko login chahiye. Stories ke baghair baki features independently configure ho saktay hain. Yeh setup **sirf apne trusted operator account** ke liye hai:

1. Apne computer par isolated Python environment mein `pip install instaloader`.
2. Local terminal mein `instaloader --login YOUR_INSTAGRAM_USERNAME` run karein. Password/2FA sirf official local tool prompt mein dein; chat, GitHub, website visitors ya logs mein nahin.
3. Tool jo session-file path print kare us **local, apni banayi hui** file ko use karein. Instaloader session sensitive hoti hai, authenticated access deti hai. Unknown person ki session file kabhi load na karein; format may involve Python pickle deserialization.
4. Apni trusted local session file ki exact bytes ko base64 encode karein. Session path replace karein:

```bash
python -c "import base64,pathlib; print(base64.b64encode(pathlib.Path('PATH_TO_YOUR_SESSION_FILE').read_bytes()).decode())"
```

   Output password jaisa secret hai; chat/GitHub mein paste na karein. Render **Environment** mein `IG_SESSION_B64` ki secret value ke taur par paste karein. App startup par exact bytes ko private temporary file (mode 600) mein decode karti hai. Base64 encryption nahin hai; is value ko credential samjhein. Sirf apni banayi trusted session file load karein, kyun ke upstream session loading may deserialize pickle.
5. Environment set karein:

```text
IG_USERNAME=YOUR_INSTAGRAM_USERNAME
IG_SESSION_B64=<base64-of-your-own-session-file>
APP_TOKEN=<your-long-random-secret>
ALLOW_PUBLIC=false
```

   Alternative: platform par actual binary secret file available ho to `IG_SESSION_FILE=/etc/secrets/instagram.session` use karein aur `IG_SESSION_B64` unset rakhein. Text field mein raw binary session paste na karein. Base64 mode mein `IG_SESSION_FILE` automatically set hota hai.
6. Redeploy karein. Direct file mode use kar rahe hon to file user `appuser` (UID 10001) ke liye readable ho.
7. URL example: `https://www.instagram.com/stories/USERNAME/STORY_ID/`.
8. **Download video** ya **Download images / thumbnail** select karein. Metadata action bhi available hai. Own/permitted public-profile story use karein. Specific story ID required; username-only mass collection nahin.
9. Session expire/checkpoint ho to local official flow se renew karein. Instagram challenge, block ya unavailable story ko bypass nahin kiya jata. App private profiles ko reject karti hai, chahe session us profile ko follow karti ho.

Local Docker story session example (copy apni authorized session to `instagram.session`, .gitignore already excludes it):

```bash
docker run --rm --env-file .env -p 10000:10000 \
  -e IG_USERNAME=YOUR_INSTAGRAM_USERNAME \
  -e IG_SESSION_FILE=/run/secrets/instagram.session \
  -v "$PWD/instagram.session:/run/secrets/instagram.session:ro" \
  media-workbench
```

**Public visitors ke liye shared Instagram login deploy na karein.** APP_TOKEN jitne logon ke paas hogi woh same job space use karenge. This is a trusted single-owner/small-team tool, not per-user isolation.

## 7. API usage

All `/api/jobs` and `/api/files` routes need `Authorization: Bearer APP_TOKEN`. `/healthz` aur non-secret `/api/config` public hain. Access token URL/query string mein nahin bheja jata.

```bash
curl -X POST https://YOUR-SERVICE.onrender.com/api/jobs \
  -H "Authorization: Bearer YOUR_APP_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=YOURVIDEOID","action":"metadata","language":"en","rights_confirmed":true}'
```

`YOURVIDEOID` ko real 11-character video ID se replace karein. Response mein returned job ID use karein:

```bash
curl https://YOUR-SERVICE.onrender.com/api/jobs/JOB_ID \
  -H "Authorization: Bearer YOUR_APP_TOKEN"

curl https://YOUR-SERVICE.onrender.com/api/files/JOB_ID/metadata.json \
  -H "Authorization: Bearer YOUR_APP_TOKEN" -o metadata.json
```

Actions: `metadata`, `video`, `images`, `transcript`, `audio_transcript`, `seo`.
Statuses: `queued`, `running`, `done`, `error`. Submission returns 202; processing is asynchronous. Job polling is required.

## 8. Limits, storage aur security

- Exactly **one uvicorn worker and one service instance**. Do not scale replicas or add uvicorn workers: job registry/process admission is in memory. No Redis/database needed for this private small app.
- One active extraction at a time; global 12 submissions/minute; up to 20 retained jobs. 429 means wait, not refresh repeatedly.
- Output/file: default 80 MB; allowed configuration 5–250 MB. Worker temporary cap is `3 * MAX_FILE_MB`, allowing separate tracks and merge. `MAX_DISK_MB` must be at least that cap. Existing outputs reserve space; use expiry or smaller limits if busy.
- Default job deadline 300 seconds. Whole worker process group is killed on timeout/space limit, including FFmpeg/yt-dlp.
- Outputs expire 30 minutes **after completion**, with cleanup approximately every 30 seconds or on access. Temporary files are deleted on failed jobs. Jobs and outputs deliberately do not survive service restart/redeploy. Render filesystem is ephemeral. Do not attach persistent storage expecting job history.
- Only canonical YouTube/Instagram HTTPS source URLs; no arbitrary download proxy, shell execution from user strings, raw extractor dump, user cookie upload, visitor session upload or per-request API-key input.
- Direct CDN downloads use narrow domain checks, public-address checks, response/type/size checks and no redirects. Keep container egress firewall/network controls if exposed beyond trusted users; application checks are not a replacement for network-level SSRF isolation. yt-dlp and Instaloader are upstream libraries with their own network behavior.
- Access key browser **tab sessionStorage** mein retained hoti hai. Use **Forget key** on shared devices. Same-key trusted users can read each other's results if IDs shared. No per-user accounts/isolation.
- AI audio mode sends selected media's audio to OpenAI; generator mode sends source metadata. Provider charges/retention policies apply. Set provider budgets and avoid sensitive content.
- `ALLOW_PUBLIC=true` without APP_TOKEN deliberately exposes jobs/results to unauthenticated users and paid API consumption if configured. **Do not use it for a public paid-AI service.** Stories refuse to work without APP_TOKEN. Keep default private configuration.
- Before launching an anonymous commercial site: real user accounts, per-user quotas/isolation, queue+Redis, external object storage, network egress controls, audited outbound requests, abuse prevention, logging/redaction, legal/privacy/terms pages and monitoring are needed. This ZIP is not that production platform.
- Use fresh dependencies and maintain them. Requirements use compatible version ranges, not a reproducibility lockfile. After successful deployment freeze tested versions if reproducibility matters; keep scheduled extractor/security updates.

## 9. Common errors

**Build `No matching distribution` / DNS failure:** build machine internet/package index access check karein. See VALIDATION.md for the preparation sandbox's actual network limitation.

**Health check failed:** Docker selected hai? Root path sahi hai? `APP_TOKEN` configured hai? `MAX_DISK_MB >= 3 * MAX_FILE_MB` hai? Logs inspect karein, but keys/session files public share na karein.

**401:** website Site access key field mein APP_TOKEN chahiye, Instagram password ya OpenAI key nahin.

**403 / sign-in / bot / 429 / extraction failure:** public hona enough nahin; Render datacenter IP platform block kar sakti hai. Short own public source on local Docker se compare karein; update yt-dlp/Instaloader and redeploy. Official permitted integration/provider may be necessary for a durable commercial service. No proxy rotation or bot/login bypass provided.

**YouTube no formats / JS runtime problem:** Docker use karein; `node --version`, `ffmpeg -version`, `python -m yt_dlp --version` check karein. `pip install -U 'yt-dlp[default]'` updates matching EJS solver too. Node 22 enabled by worker's `--js-runtimes node`.

**No captions:** selected language unavailable. English/Urdu/Hindi/Arabic mein available track try karein, warna optional paid audio transcription. No guessed/fabricated transcripts.

**Instagram images not available:** anonymous access restricted, removed post, private profile or changed extraction endpoint. Session is deliberately only used for story flow, not as a blanket fallback.

**Story failed:** exact active story URL, authorized session file, IG_USERNAME, file readability, non-private source and APP_TOKEN verify karein. File upload being binary vs text matters. See section 6.

**AI feature disabled / provider error:** OPENAI_API_KEY server side add karein; billing/usage/model access check; redeploy. Audio transcoding needs FFmpeg. Images and silent media don't produce meaningful speech transcripts.

**429 busy/storage:** current job finish hone dein. Old results TTL ke baad expire hongay. At most one job runs. If a large job cannot fit beside retained outputs, wait for expiry.

**File 404:** temporary result expired or server restarted. Link resubmit karein.

## 10. Testing

Offline engine tests (requests installed ho):

```bash
python -m unittest discover -s tests -p test_engine.py -v
```

Full API + engine suite:

```bash
pip install -r requirements-dev.txt
pytest -q
```

GitHub Actions push/PR par test suite chalati hai. Tests mocks use karti hain; passing tests platform availability prove nahin karti. Deploy hone ke baad manual smoke test:

1. `/healthz` -> `{"status":"ok"}`.
2. Wrong access key -> 401; correct key -> new job allowed.
3. Apni YouTube public short video -> metadata -> thumbnail -> video with sound.
4. Available caption language -> TXT/JSON; unavailable language -> clear error.
5. Apni public IG photo/carousel -> images, phir Reel -> video.
6. Authorized own/public-profile active story -> video/image (session configured ho).
7. Optional AI key and budget configured -> short audio transcript + generated metadata; inspect accuracy and provider usage.
8. Wait expiry -> old output unavailable. Redeploy -> old job unavailable, expected.

## 11. References

- yt-dlp: https://github.com/yt-dlp/yt-dlp
- YouTube JS runtime / EJS: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- Instaloader public Python API: https://instaloader.github.io/as-module.html
- Stories/session requirements: https://instaloader.github.io/module/instaloader.html
- Render Docker: https://render.com/docs/docker
- Render Web Services: https://render.com/docs/web-services
- Ephemeral storage: https://render.com/docs/disks
- Render secret files: https://render.com/docs/configure-environment-variables
- OpenAI audio API: https://platform.openai.com/docs/api-reference/audio

Sources change; deployment dashboard and upstream docs remain authoritative. See VALIDATION.md for what was and was not actually tested for this bundle.
