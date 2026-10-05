/**
 * ScamShield API client.
 *
 * Two transports, picked automatically from the configured API URL:
 *
 *   Flask  — POST /predict, /explain, /batch_predict, /check-domain
 *            Supports the AES-256-CBC encrypted channel (/predict_secure).
 *   Space  — the Gradio API on a Hugging Face Space
 *            (/gradio_api/call/<name>). No encrypted channel: those endpoints
 *            take a JSON string and return JSON.
 *
 * Default points at the deployed Space so a fresh install works out of the box;
 * switch to http://<your-ip>:5000 in Settings to develop against the local
 * Flask backend.
 */

import { encryptMessage, fetchEncryptionKey } from '../utils/encryption';

let BASE_URL = 'https://existedyear-scamshield.hf.space';

export function setBaseUrl(url) {
  BASE_URL = url.replace(/\/+$/, '');
}

export function getBaseUrl() {
  return BASE_URL;
}

/** True when the base URL is a Hugging Face Space, which speaks the Gradio API. */
function isSpace(url) {
  return /\.hf\.space/i.test(url);
}

function isSpaceMode() {
  return isSpace(BASE_URL);
}

// ── Flask transport ───────────────────────────────────────────────────────────

async function post(endpoint, body) {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `API error ${res.status}`);
  }
  return res.json();
}

async function get(endpoint) {
  const res = await fetch(`${BASE_URL}${endpoint}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `API error ${res.status}`);
  }
  return res.json();
}

// ── Gradio (Space) transport ──────────────────────────────────────────────────
// Gradio is queue-based: POST starts a run and returns an event id, then the
// result is streamed back over SSE on a second request.

async function gradioCall(apiName, args) {
  const start = await fetch(`${BASE_URL}/gradio_api/call/${apiName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: args }),
  });

  if (!start.ok) {
    throw new Error(`Space rejected ${apiName} (${start.status})`);
  }

  const { event_id: eventId } = await start.json();
  const stream = await fetch(`${BASE_URL}/gradio_api/call/${apiName}/${eventId}`);
  const raw = await stream.text();

  let out = null;
  let failure = null;

  for (const line of raw.split('\n')) {
    if (!line.startsWith('data:')) continue;
    let payload;
    try {
      payload = JSON.parse(line.slice(5).trim());
    } catch (_) {
      continue;
    }
    if (payload === null) continue;
    // A failed run reports the error in the payload instead of a value.
    if (payload && typeof payload === 'object' && payload.error) {
      failure = payload.error;
      continue;
    }
    out = payload;
  }

  if (failure) throw new Error(failure);
  if (out === null) throw new Error(`${apiName} returned no data`);

  const value = Array.isArray(out) ? out[0] : out;
  return typeof value === 'string' ? JSON.parse(value) : value;
}

// ── Public surface ────────────────────────────────────────────────────────────

/**
 * Fetch & cache the server's AES-256 key (Flask only).
 * Safe to call anywhere — no-ops against a Space.
 */
export async function initEncryption() {
  if (isSpaceMode()) return null;
  return fetchEncryptionKey(BASE_URL);
}

/**
 * Predict via the AES-256-CBC encrypted channel (Flask only).
 * Against a Space this falls back to the plaintext HTTPS path, since the
 * Space has no endpoint that accepts an encrypted body.
 */
export async function predictSecure(message) {
  if (isSpaceMode()) return predictMessage(message);
  const ciphertext = await encryptMessage(message);
  return post('/predict_secure', { message: ciphertext });
}

/**
 * Predict a single message.
 * @returns {{ label, confidence, risk_level, language, url_signals, text_signals }}
 */
export async function predictMessage(message) {
  if (isSpaceMode()) return gradioCall('predict', [message]);
  return post('/predict', { message });
}

/**
 * SHAP explanation for a message.
 * @returns {{ label, confidence, top_spam_words, top_ham_words }}
 */
export async function explainMessage(message) {
  if (isSpaceMode()) return gradioCall('explain', [message]);
  return post('/explain', { message });
}

/**
 * Batch predict. The Space exposes no batch endpoint, so this fans out
 * sequentially — which also avoids tripping the ZeroGPU queue.
 * @returns {{ results[], count }}
 */
export async function batchPredict(messages) {
  if (isSpaceMode()) {
    const results = [];
    for (const message of messages) {
      results.push(await gradioCall('predict', [message]));
    }
    return { results, count: results.length };
  }
  return post('/batch_predict', { messages });
}

/**
 * Domain safety check via Google Safe Browsing.
 * @returns {{ domain, is_legitimate, is_malicious, status }}
 */
export async function checkDomain(domain) {
  if (isSpaceMode()) return gradioCall('check_domain', [domain]);
  return post('/check-domain', { domain });
}

/**
 * Reachability check for the Settings screen.
 * @returns {{ status, model }}
 */
export async function healthCheck() {
  if (isSpaceMode()) {
    const res = await fetch(`${BASE_URL}/gradio_api/info`);
    if (!res.ok) throw new Error(`Space unreachable (${res.status})`);
    const info = await res.json();
    return { status: 'ok', model: 'ScamShield (XLM-RoBERTa · Space/ZeroGPU)', transport: 'gradio' };
  }
  return { ...(await get('/health')), transport: 'flask' };
}