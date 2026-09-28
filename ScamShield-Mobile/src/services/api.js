/**
 * ScamShield API client — communicates with the Flask backend
 */

import { encryptMessage, fetchEncryptionKey } from '../utils/encryption';

let BASE_URL = 'http://localhost:5000';

export function setBaseUrl(url) {
  BASE_URL = url.replace(/\/+$/, '');
}

export function getBaseUrl() {
  return BASE_URL;
}

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

// ── Endpoints ──────────────────────────────────────────────────────────────────

/**
 * Fetch & cache the server's AES-256 key. Call once on app start.
 */
export async function initEncryption() {
  return fetchEncryptionKey(BASE_URL);
}

/**
 * Predict via AES-256-CBC encrypted channel (used by SMS monitor).
 * @returns {{ label, confidence, risk_level, language, encryption_used, ... }}
 */
export async function predictSecure(message) {
  const ciphertext = await encryptMessage(message);
  return post('/predict_secure', { message: ciphertext });
}

/**
 * Predict without encryption (fallback / manual scan screen).
 * @returns {{ label, confidence, risk_level, url_signals, text_signals }}
 */
export async function predictMessage(message) {
  return post('/predict', { message });
}

/**
 * Get SHAP explanation for a message.
 * @returns {{ label, confidence, top_spam_words, top_ham_words, feature_importances }}
 */
export async function explainMessage(message) {
  return post('/explain', { message });
}

/**
 * Batch predict multiple messages.
 * @returns {{ results[], count }}
 */
export async function batchPredict(messages) {
  return post('/batch_predict', { messages });
}

/**
 * Check domain safety via Google Safe Browsing.
 * @returns {{ domain, is_legitimate, status }}
 */
export async function checkDomain(domain) {
  return post('/check-domain', { domain });
}

/**
 * Health check.
 * @returns {{ status, model, encryption }}
 */
export async function healthCheck() {
  return get('/health');
}
