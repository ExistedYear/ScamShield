/**
 * AES-256-CBC encryption for SMS messages before sending to the API.
 *
 * The key is fetched from /api/encryption-key on first launch and cached
 * in AsyncStorage, falling back to the built-in key below when the server is
 * unreachable (e.g. offline first boot).
 *
 * NOTE: the encrypted channel only exists on the Flask backend
 * (POST /predict_secure). When the app is pointed at a Hugging Face Space the
 * transport in services/api.js switches to the Space's JSON API over HTTPS,
 * where the message travels in plaintext — the Space does not expose a
 * custom binary payload endpoint.
 */

import CryptoJS from 'crypto-js';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY_STORAGE = 'scamshield_enc_key';

// Must match APP_TOKEN in the server .env — guards GET /api/encryption-key.
const APP_TOKEN = 'ss-AvmRL7ST5IxsYLDymOl4AI84NDMCDdcP';

// Must match SMS_ENCRYPTION_KEY in the server .env (64 hex chars = 32 bytes).
// Only used when the Flask backend cannot be reached to hand over a fresh key.
const DEFAULT_KEY = '1e56bebceaf8862dd9906bdef16b7868c5487fe15816174ad4c4a405a3597ce7';

let _cachedKey = null;

export async function getEncryptionKey() {
  if (_cachedKey) return _cachedKey;

  const stored = await AsyncStorage.getItem(KEY_STORAGE);
  // Fall back to the built-in key so the app works offline on first boot.
  _cachedKey = stored || DEFAULT_KEY;
  return _cachedKey;
}

export async function fetchEncryptionKey(apiUrl) {
  try {
    const res = await fetch(`${apiUrl}/api/encryption-key`, {
      method: 'GET',
      headers: { 'X-App-Token': APP_TOKEN },
    });

    if (res.ok) {
      const data = await res.json();
      if (data.key) {
        _cachedKey = data.key;
        await AsyncStorage.setItem(KEY_STORAGE, data.key);
        return data.key;
      }
    }
  } catch (_) {
    // Keep using a previously cached key when the server is temporarily offline.
  }

  return await getEncryptionKey();
}

export async function encryptMessage(plaintext) {
  const keyHex = await getEncryptionKey();
  const key = CryptoJS.enc.Hex.parse(keyHex);
  const iv = CryptoJS.lib.WordArray.random(16);

  const encrypted = CryptoJS.AES.encrypt(plaintext, key, {
    iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7,
  });

  const combined = iv.concat(encrypted.ciphertext);
  return CryptoJS.enc.Base64.stringify(combined);
}