import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput,
  TouchableOpacity, Switch, Alert, ActivityIndicator,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@react-navigation/native';
import { getSettings, saveSettings, clearScanHistory, getScanHistory } from '../utils/storage';
import { healthCheck, setBaseUrl, getBaseUrl } from '../services/api';
import { startMonitoring, stopMonitoring, smsLog } from '../services/smsMonitor';

export default function SettingsScreen({ onToggleTheme }) {
  const { colors, dark } = useTheme();
  const [settings, setSettings] = useState(null);
  const [apiUrl, setApiUrl] = useState('');
  const [apiStatus, setApiStatus] = useState(null); // 'ok', 'error', null
  const [checking, setChecking] = useState(false);
  const [historyCount, setHistoryCount] = useState(0);

  useEffect(() => {
    (async () => {
      const s = await getSettings();
      setSettings(s);
      setApiUrl(s.apiUrl || getBaseUrl());
      const h = await getScanHistory();
      setHistoryCount(h.length);
    })();
  }, []);

  const updateSetting = async (key, val) => {
    const updated = { ...settings, [key]: val };
    setSettings(updated);
    await saveSettings(updated);
  };

  const handleAutoScan = async (enabled) => {
    await updateSetting('autoScan', enabled);
    if (enabled) {
      const { ok, reason } = await startMonitoring();
      if (!ok) {
        await updateSetting('autoScan', false);
        Alert.alert('Auto-scan unavailable', reason || 'Unable to start SMS monitoring.');
      }
    } else {
      await stopMonitoring();
    }
  };

  const handleSaveUrl = async () => {
    const url = apiUrl.trim().replace(/\/+$/, '');
    if (!url) return;
    setBaseUrl(url);
    await updateSetting('apiUrl', url);
    handleCheckApi();
  };

  const handleCheckApi = async () => {
    setChecking(true); setApiStatus(null);
    try {
      const res = await healthCheck();
      setApiStatus(res.status === 'ok' ? 'ok' : 'error');
    } catch { setApiStatus('error'); }
    setChecking(false);
  };

  const handleClearHistory = () => {
    Alert.alert('Clear History', 'Delete all scan history from this device?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Clear', style: 'destructive', onPress: async () => { await clearScanHistory(); setHistoryCount(0); } },
    ]);
  };

  if (!settings) return <View style={[s.root, { backgroundColor: colors.bg }]} />;

  return (
    <ScrollView style={[s.root, { backgroundColor: colors.bg }]} contentContainerStyle={s.content}>
      {/* API Configuration */}
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={s.cardH}>
          <Feather name="server" size={16} color={colors.accent} />
          <Text style={[s.cardTitle, { color: colors.text }]}>API Server</Text>
        </View>
        <Text style={[s.desc, { color: colors.text2 }]}>
          Connect to your Flask API server running the smishing detection model.
        </Text>
        <Text style={[s.label, { color: colors.text3 }]}>SERVER URL</Text>
        <View style={s.urlRow}>
          <TextInput
            style={[s.urlInput, { backgroundColor: colors.inputBg, borderColor: colors.border, color: colors.text }]}
            value={apiUrl}
            onChangeText={setApiUrl}
            placeholder="http://192.168.1.100:5000"
            placeholderTextColor={colors.text3}
            autoCapitalize="none"
            autoCorrect={false}
          />
          <TouchableOpacity onPress={handleSaveUrl} style={[s.urlBtn, { backgroundColor: colors.accent }]}>
            {checking ? <ActivityIndicator size="small" color="#fff" /> : <Feather name="check" size={16} color="#fff" />}
          </TouchableOpacity>
        </View>
        {apiStatus === 'ok' && (
          <View style={[s.statusBox, { backgroundColor: colors.greenSoft, borderColor: colors.greenBorder }]}>
            <Feather name="check-circle" size={13} color={colors.green} />
            <Text style={[s.statusT, { color: colors.green }]}>Connected — Model loaded</Text>
          </View>
        )}
        {apiStatus === 'error' && (
          <View style={[s.statusBox, { backgroundColor: colors.redSoft, borderColor: colors.redBorder }]}>
            <Feather name="x-circle" size={13} color={colors.red} />
            <Text style={[s.statusT, { color: colors.red }]}>Connection failed — check URL and server</Text>
          </View>
        )}
      </View>

      {/* Preferences */}
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={s.cardH}>
          <Feather name="sliders" size={16} color={colors.accent} />
          <Text style={[s.cardTitle, { color: colors.text }]}>Preferences</Text>
        </View>

        <View style={s.row}>
          <View style={{ flex: 1 }}>
            <Text style={[s.rowTitle, { color: colors.text }]}>Auto-scan SMS</Text>
            <Text style={[s.rowDesc, { color: colors.text3 }]}>Automatically analyze new incoming messages</Text>
          </View>
          <Switch value={settings.autoScan} onValueChange={handleAutoScan}
            trackColor={{ false: colors.border, true: colors.accentSoft }}
            thumbColor={settings.autoScan ? colors.accent : colors.text3} />
        </View>

        <View style={[s.rowDiv, { borderTopColor: colors.border }]} />

        <View style={s.row}>
          <View style={{ flex: 1 }}>
            <Text style={[s.rowTitle, { color: colors.text }]}>Threat Notifications</Text>
            <Text style={[s.rowDesc, { color: colors.text3 }]}>Show alerts when threats are detected</Text>
          </View>
          <Switch value={settings.notifications} onValueChange={v => updateSetting('notifications', v)}
            trackColor={{ false: colors.border, true: colors.accentSoft }}
            thumbColor={settings.notifications ? colors.accent : colors.text3} />
        </View>

        <View style={[s.rowDiv, { borderTopColor: colors.border }]} />

        <View style={s.row}>
          <View style={{ flex: 1 }}>
            <Text style={[s.rowTitle, { color: colors.text }]}>Dark Mode</Text>
            <Text style={[s.rowDesc, { color: colors.text3 }]}>Use dark theme throughout the app</Text>
          </View>
          <Switch value={dark} onValueChange={() => onToggleTheme?.()}
            trackColor={{ false: colors.border, true: colors.accentSoft }}
            thumbColor={dark ? colors.accent : colors.text3} />
        </View>
      </View>

      {/* Data */}
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={s.cardH}>
          <Feather name="database" size={16} color={colors.accent} />
          <Text style={[s.cardTitle, { color: colors.text }]}>Data</Text>
        </View>
        <View style={s.row}>
          <View style={{ flex: 1 }}>
            <Text style={[s.rowTitle, { color: colors.text }]}>Scan History</Text>
            <Text style={[s.rowDesc, { color: colors.text3 }]}>{historyCount} messages scanned</Text>
          </View>
          <TouchableOpacity onPress={handleClearHistory} style={[s.clearBtn, { borderColor: colors.redBorder }]}>
            <Feather name="trash-2" size={13} color={colors.red} />
            <Text style={[s.clearT, { color: colors.red }]}>Clear</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* About */}
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={s.cardH}>
          <Feather name="info" size={16} color={colors.accent} />
          <Text style={[s.cardTitle, { color: colors.text }]}>About</Text>
        </View>
        <Text style={[s.aboutT, { color: colors.text2 }]}>
          ScamShield AI uses an XLM-RoBERTa + hand-crafted features model to detect SMS phishing (smishing) attacks in real-time, supporting English, Hindi, and Hinglish messages.
        </Text>
        <View style={s.aboutRow}>
          <Text style={[s.aboutK, { color: colors.text3 }]}>Model</Text>
          <Text style={[s.aboutV, { color: colors.text }]}>SmishingDetector (XLM-RoBERTa · EN/HI/Hinglish)</Text>
        </View>
        <View style={s.aboutRow}>
          <Text style={[s.aboutK, { color: colors.text3 }]}>API</Text>
          <Text style={[s.aboutV, { color: colors.text }]}>Flask + SHAP Explainability</Text>
        </View>
        <View style={s.aboutRow}>
          <Text style={[s.aboutK, { color: colors.text3 }]}>Version</Text>
          <Text style={[s.aboutV, { color: colors.text }]}>1.0.0</Text>
        </View>
      </View>

      {/* SMS Debug Log */}
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={s.cardH}>
          <Feather name="terminal" size={16} color={colors.accent} />
          <Text style={[s.cardTitle, { color: colors.text }]}>SMS Debug Log</Text>
        </View>
        {smsLog.length === 0 ? (
          <Text style={[s.desc, { color: colors.text3 }]}>No SMS events yet. Open the Inbox tab and toggle monitoring.</Text>
        ) : (
          <View style={[s.logBox, { backgroundColor: colors.inputBg, borderColor: colors.border }]}>
            {smsLog.slice(0, 25).map((entry, i) => (
              <Text key={i} style={[s.logLine, { color: colors.text2 }]}>{entry}</Text>
            ))}
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1 },
  content: { padding: 16, paddingBottom: 100 },
  card: { borderWidth: 1, borderRadius: 14, padding: 18, marginBottom: 14, elevation: 3 },
  cardH: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  cardTitle: { fontSize: 16, fontWeight: '700' },
  desc: { fontSize: 13, lineHeight: 20, marginBottom: 14 },
  label: { fontSize: 10, fontWeight: '700', letterSpacing: 0.9, textTransform: 'uppercase', marginBottom: 6 },
  urlRow: { flexDirection: 'row', gap: 8 },
  urlInput: { flex: 1, borderWidth: 1.5, borderRadius: 10, fontSize: 13, padding: 12 },
  urlBtn: { width: 46, borderRadius: 10, alignItems: 'center', justifyContent: 'center', elevation: 3 },
  statusBox: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1, borderRadius: 8, padding: 10, marginTop: 10 },
  statusT: { fontSize: 12, fontWeight: '600' },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8 },
  rowTitle: { fontSize: 14, fontWeight: '600', marginBottom: 2 },
  rowDesc: { fontSize: 12 },
  rowDiv: { borderTopWidth: 1, marginVertical: 4 },
  clearBtn: { flexDirection: 'row', alignItems: 'center', gap: 5, borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 7 },
  clearT: { fontSize: 12, fontWeight: '600' },
  aboutT: { fontSize: 13, lineHeight: 20, marginBottom: 12 },
  aboutRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 5 },
  aboutK: { fontSize: 12, fontWeight: '600' },
  aboutV: { fontSize: 12, fontWeight: '600' },
  logBox: { borderWidth: 1, borderRadius: 10, padding: 10, maxHeight: 400 },
  logLine: { fontSize: 10, fontFamily: 'monospace', lineHeight: 16, marginBottom: 2 },
});
