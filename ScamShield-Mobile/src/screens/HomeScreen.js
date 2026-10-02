import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  RefreshControl, ActivityIndicator, StatusBar, Switch, Platform, Alert,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme, useFocusEffect } from '@react-navigation/native';
import MessageCard from '../components/MessageCard';
import {
  readInboxSms, getDemoMessages, simulateIncomingSms,
  startMonitoring, stopMonitoring, isMonitoring, scanNewMessages,
} from '../services/smsMonitor';
import { predictSecure, predictMessage, initEncryption } from '../services/api';
import { addScanResult, getScanHistory } from '../utils/storage';

const USE_REAL_SMS = Platform.OS === 'android';

export default function HomeScreen({ navigation }) {
  const { colors, dark } = useTheme();
  const [messages,    setMessages]    = useState([]);
  const [scanResults, setScanResults] = useState({});
  const [scanning,    setScanning]    = useState(null);
  const [refreshing,  setRefreshing]  = useState(false);
  const [stats,       setStats]       = useState({ total: 0, threats: 0, safe: 0 });
  const [monitoring,  setMonitoring]  = useState(false);
  const [monitorBusy, setMonitorBusy] = useState(false);
  const pollRef = useRef(null);

  // ── Data loading ──────────────────────────────────────────────────────────

  const loadMessages = useCallback(async () => {
    if (USE_REAL_SMS) {
      const real = await readInboxSms(30);
      setMessages(real.length ? real : getDemoMessages());
    } else {
      setMessages(getDemoMessages());
    }
  }, []);

  const loadHistory = useCallback(async () => {
    const history = await getScanHistory();
    const map = {};
    history.forEach((h) => { if (h.messageId) map[h.messageId] = h; });
    setScanResults(map);
    const total   = history.length;
    const threats = history.filter((h) => h.label === 'spam' && (h.risk_level === 'high' || h.risk_level === 'medium')).length;
    setStats({ total, threats, safe: total - threats });
  }, []);

  const loadData = useCallback(async () => {
    await Promise.all([loadMessages(), loadHistory()]);
  }, [loadMessages, loadHistory]);

  useFocusEffect(useCallback(() => { loadData(); }, [loadData]));

  // ── Init encryption key on mount ─────────────────────────────────────────

  useEffect(() => {
    (async () => {
      initEncryption().catch(() => {});
      const active = await isMonitoring();
      setMonitoring(active);
      if (active) {
        await scanNewMessages().catch(() => {});
        await loadData();
      }
    })();
  }, [loadData]);

  // ── Foreground polling (while app is open) ────────────────────────────────

  useEffect(() => {
    if (!monitoring || !USE_REAL_SMS) return;
    pollRef.current = setInterval(async () => {
      await scanNewMessages().catch(() => {});
      await loadData();
    }, 15000); // refresh message list every 15s
    return () => clearInterval(pollRef.current);
  }, [monitoring, loadData]);

  // ── Actions ───────────────────────────────────────────────────────────────

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const handleScan = async (message) => {
    setScanning(message.id);
    try {
      // Use encrypted channel when available, plain fallback otherwise
      const result = await predictSecure(message.body).catch(() => predictMessage(message.body));
      const scanData = { messageId: message.id, address: message.address, body: message.body, ...result };
      await addScanResult(scanData);
      setScanResults((prev) => ({ ...prev, [message.id]: scanData }));
      setStats((prev) => ({
        total:   prev.total + 1,
        threats: result.label === 'spam' && result.risk_level !== 'low' ? prev.threats + 1 : prev.threats,
        safe:    result.label !== 'spam' || result.risk_level === 'low' ? prev.safe    + 1 : prev.safe,
      }));
    } catch (err) {
      const fallback = {
        messageId: message.id, address: message.address, body: message.body,
        label: 'unknown', confidence: 0, risk_level: 'low', error: err.message,
      };
      setScanResults((prev) => ({ ...prev, [message.id]: fallback }));
    }
    setScanning(null);
  };

  const handleSimulate = () => {
    const newMsg = simulateIncomingSms();
    setMessages((prev) => [newMsg, ...prev]);
  };

  const toggleMonitoring = async () => {
    setMonitorBusy(true);
    if (monitoring) {
      await stopMonitoring();
      setMonitoring(false);
    } else {
      const { ok, reason } = await startMonitoring();
      setMonitoring(ok);
      if (ok) {
        await scanNewMessages().catch(() => {});
        await loadData();
      } else if (reason) {
        Alert.alert('Monitoring unavailable', reason);
      }
    }
    setMonitorBusy(false);
  };

  // ── Render ────────────────────────────────────────────────────────────────

  const renderHeader = () => (
    <View>
      {/* Stats Row */}
      <View style={styles.statsRow}>
        {[
          { icon: 'shield',         color: colors.accent, val: stats.total,   label: 'Scanned'  },
          { icon: 'alert-triangle', color: colors.red,    val: stats.threats, label: 'Threats'  },
          { icon: 'check-circle',   color: colors.green,  val: stats.safe,    label: 'Safe'     },
        ].map(({ icon, color, val, label }) => (
          <View key={label} style={[styles.statCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Feather name={icon} size={18} color={color} />
            <Text style={[styles.statNum, { color }]}>{val}</Text>
            <Text style={[styles.statLabel, { color: colors.text3 }]}>{label}</Text>
          </View>
        ))}
      </View>

      {/* Live Monitor Toggle */}
      <View style={[styles.monitorBanner, {
        backgroundColor: monitoring ? colors.accentSoft : colors.surface,
        borderColor:     monitoring ? colors.accent      : colors.border,
      }]}>
        <View style={styles.monitorLeft}>
          <Feather name="radio" size={16} color={monitoring ? colors.accent : colors.text3} />
          <View style={styles.monitorText}>
            <Text style={[styles.monitorTitle, { color: monitoring ? colors.accent : colors.text }]}>
              {monitoring ? 'Live Monitoring ON' : 'Live Monitoring OFF'}
            </Text>
            <Text style={[styles.monitorSub, { color: colors.text3 }]}>
              {monitoring
                ? 'Auto-scanning incoming SMS • AES-256 encrypted'
                : 'Enable to auto-scan incoming messages'}
            </Text>
          </View>
        </View>
        {monitorBusy
          ? <ActivityIndicator size="small" color={colors.accent} />
          : <Switch
              value={monitoring}
              onValueChange={toggleMonitoring}
              trackColor={{ false: colors.border, true: colors.accent }}
              thumbColor="#fff"
            />
        }
      </View>

      {/* Action Buttons */}
      <View style={styles.actionRow}>
        <TouchableOpacity onPress={handleSimulate} style={[styles.actionBtnOutline, { borderColor: colors.border }]} activeOpacity={0.8}>
          <Feather name="plus" size={14} color={colors.text2} />
          <Text style={[styles.actionBtnOutlineText, { color: colors.text2 }]}>Simulate SMS</Text>
        </TouchableOpacity>
      </View>

      <Text style={[styles.sectionLabel, { color: colors.text3 }]}>
        <Feather name="inbox" size={11} /> INBOX — {messages.length} MESSAGES
        {USE_REAL_SMS ? '  •  LIVE' : '  •  DEMO'}
      </Text>
    </View>
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.bg }]}>
      <StatusBar barStyle={dark ? 'light-content' : 'dark-content'} backgroundColor={colors.bg} />
      <FlatList
        data={messages}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
        ListHeaderComponent={renderHeader}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.accent} />}
        renderItem={({ item }) => (
          <View>
            <MessageCard
              message={item}
              scanResult={scanResults[item.id]}
              onPress={() => navigation.navigate('Detail', { message: item, scanResult: scanResults[item.id] })}
              onScan={scanning === item.id ? null : () => handleScan(item)}
            />
            {scanning === item.id && (
              <View style={[styles.scanningOverlay, { backgroundColor: colors.accentSoft }]}>
                <ActivityIndicator size="small" color={colors.accent} />
                <Text style={[styles.scanningText, { color: colors.accent }]}>Analyzing… 🔒</Text>
              </View>
            )}
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Feather name="inbox" size={48} color={colors.text3} />
            <Text style={[styles.emptyText, { color: colors.text3 }]}>No messages found</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container:  { flex: 1 },
  list:       { padding: 16, paddingBottom: 100 },
  statsRow:   { flexDirection: 'row', gap: 10, marginBottom: 14 },
  statCard:   {
    flex: 1, alignItems: 'center', paddingVertical: 16,
    borderRadius: 14, borderWidth: 1, gap: 4,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08, shadowRadius: 6, elevation: 2,
  },
  statNum:    { fontSize: 24, fontWeight: '800', fontVariant: ['tabular-nums'] },
  statLabel:  { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.5 },

  monitorBanner: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    padding: 14, borderRadius: 14, borderWidth: 1.5, marginBottom: 14,
  },
  monitorLeft:  { flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 },
  monitorText:  { flex: 1 },
  monitorTitle: { fontSize: 14, fontWeight: '700' },
  monitorSub:   { fontSize: 11, marginTop: 1 },

  actionRow:           { flexDirection: 'row', gap: 10, marginBottom: 20 },
  actionBtn:           {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 12, borderRadius: 10,
    shadowColor: '#3b82f6', shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.35, shadowRadius: 8, elevation: 4,
  },
  actionBtnText:       { color: '#fff', fontSize: 14, fontWeight: '700' },
  actionBtnOutline:    {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 12, borderRadius: 10, borderWidth: 1.5,
  },
  actionBtnOutlineText: { fontSize: 14, fontWeight: '600' },
  sectionLabel:         {
    fontSize: 10, fontWeight: '700', letterSpacing: 0.9,
    textTransform: 'uppercase', marginBottom: 12,
  },
  scanningOverlay: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, paddingVertical: 6, borderRadius: 8, marginTop: -6, marginBottom: 10,
  },
  scanningText: { fontSize: 12, fontWeight: '600' },
  empty:        { alignItems: 'center', paddingTop: 60, gap: 12 },
  emptyText:    { fontSize: 14, fontWeight: '500' },
});
