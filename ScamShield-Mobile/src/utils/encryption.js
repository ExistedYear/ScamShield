/**
 * AES-256-CBC encryption for SMS messages before sending to the API.
 *
 * The key is fetched from /api/encryption-key and cached in AsyncStorage.
 * There is intentionally no hardcoded fallback key.
 */

import CryptoJS from 'crypto-js';
import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY_STORAGE = 'scamshield_enc_key';
const APP_TOKEN = 'scamshield-dev-token';

let _cachedKey = null;

export async function getEncryptionKey() {
  if (_cachedKey) return _cachedKey;

  const stored = await AsyncStorage.getItem(KEY_STORAGE);
  if (!stored) {
    throw new Error('Encryption key has not been initialized.');
  }

  _cachedKey = stored;
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
