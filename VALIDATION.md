# Validation record

## Actually executed for this bundle

- Python syntax compilation for app.py, engine.py and tests: passed.
- JavaScript syntax check for static/app.js: passed.
- Offline engine suite: 15 tests passed. Includes URL canonicalization/host restrictions, duration guards, caption parsing/export, metadata whitelist/export, invalid actions, CDN host/private-address rejection, missing AI configuration, absent story session, image-only video error, and Instagram captions explanation.
- Browser interaction checks using real Chromium and mocked API responses: submit -> poll -> result, API error display, 390px/1440px horizontal overflow checks, and no uncaught JavaScript exceptions: passed.
- Visual review of desktop, 390px mobile, mocked-result state, mobile error state and dark theme: completed. No overlapping/overflowing page elements observed. Screenshots used fixtures, not real extracted social media.

## Not executed / not verified

- Full FastAPI runtime and its 8 included API tests: NOT executed; these tests were skipped locally because FastAPI/httpx were unavailable.
- pip installation was attempted, but the sandbox's package-index DNS/network request failed with `Failed to establish a new connection: [Errno -2] Name or service not known`. This is not evidence that the dependencies do not exist on PyPI.
- No Docker image was built in this environment.
- No real YouTube/Instagram download, thumbnail fetch, caption retrieval, story/session login, OpenAI call, GitHub push or Render deployment was performed.
- Provider/platform availability, Render IP acceptance, exact output formats, AI accuracy and account-specific API billing/model availability remain deployment-time checks.

## Before relying on this app

Run `pip install -r requirements-dev.txt && pytest -q` in an internet-enabled development environment or let GitHub Actions run it. Ensure all API tests execute rather than skip. Build Docker. Follow the manual smoke-test checklist in README.md using content you own or are authorized to process. Test a small file first, inspect audio/video quality and configure provider spending limits. Keep the default access protection; this is not an audited multi-user public production service.

The application includes real integrations, not mock extraction endpoints. Test fixtures only occur in tests. A code bundle is not a guarantee that third-party platforms will accept every request.
