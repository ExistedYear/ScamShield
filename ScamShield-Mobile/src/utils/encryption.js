/**
 * AES-256-CBC encryption for SMS messages before sending to the API.
 *
 * The key is fetched from /api/encryption-key on first launch and cached
 * in AsyncStorage. Falls back to the built-in dev key if the server is
 * unreachable (e.g. offline first boot). Set SMS_ENCRYPTION_KEY in the
 * server .env to use a custom key — both sides must match.
 */

import CryptoJS from 'crypto-js';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY_STORAGE = 'scamshield_enc_key';
const APP_TOKEN = 'scamshield-dev-token';

let _cachedKey = null;

// Fallback key — matches SMS_ENCRYPTION_KEY default in encryption.py
const DEFAULT_KEY = '5fc5555dfd4b23ecfbfbfda273cb82eb5fdfb8b25c5b1357a2568d6afa1f472e';

export async function getEncryptionKey() {
  if (_cachedKey) return _cachedKey;

  const stored = await AsyncStorage.getItem(KEY_STORAGE);
  // Fall back to built-in dev key so the app works offline on first boot
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
