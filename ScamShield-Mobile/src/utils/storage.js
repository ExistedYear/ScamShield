import AsyncStorage from '@react-native-async-storage/async-storage';

const KEYS = {
  SCAN_HISTORY: '@scamshield_scan_history',
  SETTINGS: '@scamshield_settings',
};

const DEFAULT_SETTINGS = {
  // Deployed Space by default so a fresh install works without configuration.
  // Point this at http://<your-lan-ip>:5000 to develop against local Flask —
  // that path additionally enables the AES-256-CBC encrypted channel.
  apiUrl: 'https://existedyear-scamshield.hf.space',
  autoScan: true,
  notifications: true,
  darkMode: true,
};

// ── Settings ──────────────────────────────────────────────────

export async function getSettings() {
  try {
    const raw = await AsyncStorage.getItem(KEYS.SETTINGS);
    return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : { ...DEFAULT_SETTINGS };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export async function saveSettings(settings) {
  await AsyncStorage.setItem(KEYS.SETTINGS, JSON.stringify(settings));
}

// ── Scan History ──────────────────────────────────────────────

export async function getScanHistory() {
  try {
    const raw = await AsyncStorage.getItem(KEYS.SCAN_HISTORY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export async function addScanResult(result) {
  const history = await getScanHistory();
  history.unshift({
    ...result,
    scannedAt: new Date().toISOString(),
  });
  // Keep only the last 500 entries
  const trimmed = history.slice(0, 500);
  await AsyncStorage.setItem(KEYS.SCAN_HISTORY, JSON.stringify(trimmed));
}

export async function clearScanHistory() {
  await AsyncStorage.removeItem(KEYS.SCAN_HISTORY);
}
