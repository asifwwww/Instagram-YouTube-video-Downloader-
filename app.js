'use strict';
const $ = id => document.getElementById(id);
const form = $('form');
let token = sessionStorage.getItem('media-access') || '';
$('token').value = token;
let lastResult = '';
let active = false;
function message(text, error = false) {
  $('status').hidden = false;
  $('status').textContent = text;
  $('status').classList.toggle('error', error);
}
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {...(options.headers || {}), ...(token ? {Authorization: 'Bearer ' + token} : {})}});
  if (!response.ok) {
    let data = {};
    try { data = await response.json(); } catch (_) {}
    throw new Error(typeof data.detail === 'string' ? data.detail : 'Request failed (' + response.status + '). Check the link and settings.');
  }
  return response;
}
async function download(id, file, button) {
  button.disabled = true;
  try {
    const response = await api('/api/files/' + encodeURIComponent(id) + '/' + encodeURIComponent(file.name));
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = file.name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) { message(e.message, true); }
  finally { button.disabled = false; }
}
function showResult(id, result) {
  $('results').hidden = false;
  $('result-title').textContent = result.metadata?.title ? 'Ready to use' : 'Your result';
  $('result-summary').textContent = result.metadata?.title || 'Processing completed.';
  lastResult = JSON.stringify(result.generated || result.transcript || result.metadata || result, null, 2);
  $('output').textContent = lastResult;
  $('files').replaceChildren();
  for (const file of result.files || []) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = '↓ ' + file.name + ' · ' + (file.bytes / 1024 / 1024).toFixed(2) + ' MB';
    button.addEventListener('click', () => download(id, file, button));
    $('files').appendChild(button);
  }
}
form.addEventListener('submit', async e => {
  e.preventDefault();
  if (active) return;
  active = true;
  token = $('token').value.trim();
  if (token) sessionStorage.setItem('media-access', token); else sessionStorage.removeItem('media-access');
  $('submit').disabled = true;
  $('results').hidden = true;
  message('Connecting to the source… Please keep this page open.');
  try {
    const body = {url: $('url').value.trim(), action: $('action').value, language: $('language').value, rights_confirmed: $('rights').checked};
    const created = await (await api('/api/jobs', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)})).json();
    const deadline = Date.now() + 7 * 60 * 1000;
    while (Date.now() < deadline) {
      await new Promise(resolve => setTimeout(resolve, 1500));
      const job = await (await api('/api/jobs/' + encodeURIComponent(created.id))).json();
      if (job.status === 'error') throw new Error(job.error);
      if (job.status === 'done') {
        showResult(created.id, job.result);
        message('Done. Your files are ready below.');
        return;
      }
      message('Processing your link… Large files and speech transcription can take a few minutes.');
    }
    throw new Error('Waiting timed out. The server may have restarted; try again in a moment.');
  } catch (e) { message(e.message || 'Network error. Check your connection and retry.', true); }
  finally { active = false; $('submit').disabled = false; }
});
$('forget').addEventListener('click', () => { token = ''; $('token').value = ''; sessionStorage.removeItem('media-access'); message('Access key removed from this browser tab.'); });
$('copy').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(lastResult); message('Result copied.'); }
  catch (_) { message('Clipboard unavailable. Select and copy the result manually.', true); }
});
fetch('/api/config').then(r => { if (!r.ok) throw new Error(); return r.json(); }).then(config => {
  $('access').open = config.token_required && !token;
  $('limits').textContent = config.max_file_mb + ' MB / file · ' + Math.floor(config.max_duration_seconds / 60) + ' min videos';
  if (!config.ai_enabled) {
    for (const option of $('action').options) if (['seo', 'audio_transcript'].includes(option.value)) {
      option.disabled = true; option.textContent += ' (key not configured)';
    }
  }
}).catch(() => message('Could not load site settings. Refresh after the server finishes starting.', true));
