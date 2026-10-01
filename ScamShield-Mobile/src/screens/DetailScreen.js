import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@react-navigation/native';
import { getRiskColors } from '../utils/theme';
import RiskBadge from '../components/RiskBadge';
import ConfidenceBar from '../components/ConfidenceBar';
import ShapChart from '../components/ShapChart';
import UrlAnalysis from '../components/UrlAnalysis';
import { predictMessage, explainMessage } from '../services/api';

export default function DetailScreen({ route }) {
  const { colors } = useTheme();
  const { message, scanResult: initialResult } = route.params;
  const [result, setResult] = useState(initialResult || null);
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(!initialResult);

  useEffect(() => {
    const run = async () => {
      if (!result) {
        try {
          setLoading(true);
          const pred = await predictMessage(message.body);
          setResult(pred);
        } catch {}
      }
      try {
        const expl = await explainMessage(message.body);
        setExplanation(expl);
      } catch {}
      setLoading(false);
    };
    run();
  }, []);

  if (loading && !result) {
    return (
      <View style={[s.center, { backgroundColor: colors.bg }]}>
        <ActivityIndicator size="large" color={colors.accent} />
        <Text style={[s.loadT, { color: colors.text2 }]}>Analyzing message…</Text>
      </View>
    );
  }

  const riskLevel = result?.risk_level || 'low';
  const risk = getRiskColors(riskLevel, colors);

  const formatDate = (ts) => {
    const d = new Date(ts);
    return d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });
  };

  return (
    <ScrollView style={[s.root, { backgroundColor: colors.bg }]} contentContainerStyle={s.content}>
      {/* Verdict Card */}
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: risk.border }]}>
        <View style={s.verdict}>
          <RiskBadge riskLevel={riskLevel} size="large" />
          <View style={{ flex: 1 }}>
            <Text style={[s.verdictH, { color: colors.text }]}>
              {result?.label === 'spam' ? 'Threat Detected' : result?.label === 'safe' ? 'Verified Safe' : 'Appears Legitimate'}
            </Text>
            <View style={s.riskRow}>
              <View style={[s.rDot, { backgroundColor: risk.color }]} />
              <Text style={[s.rLbl, { color: colors.text2 }]}>
                {riskLevel === 'high' ? 'High Risk' : riskLevel === 'medium' ? 'Medium Risk' : 'Low Risk'}
              </Text>
            </View>
          </View>
        </View>
      </View>

      {/* Green Channel Badge */}
      {result?.green_channel && (
        <View style={[s.gsbBadge, { backgroundColor: colors.greenSoft, borderColor: colors.greenBorder }]}>
          <Feather name="check-circle" size={15} color={colors.green} />
          <View style={{ flex: 1 }}>
            <Text style={[s.gsbTitle, { color: colors.green }]}>Green Channel Cleared</Text>
            <Text style={[s.gsbSub, { color: colors.text2 }]}>
              {result.green_reason || 'This message contains promotional content from verified sources — not a scam.'}
            </Text>
          </View>
        </View>
      )}

      {/* Message Info */}
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={s.metaRow}>
          <Feather name="user" size={13} color={colors.text3} />
          <Text style={[s.metaLabel, { color: colors.text3 }]}>From</Text>
          <Text style={[s.metaVal, { color: colors.text }]}>{message.address}</Text>
        </View>
        <View style={s.metaRow}>
          <Feather name="clock" size={13} color={colors.text3} />
          <Text style={[s.metaLabel, { color: colors.text3 }]}>Received</Text>
          <Text style={[s.metaVal, { color: colors.text }]}>{formatDate(message.date)}</Text>
        </View>
        <View style={[s.div, { borderTopColor: colors.border }]} />
        <Text style={[s.label, { color: colors.text3 }]}>FULL MESSAGE</Text>
        <View style={[s.mbox, { backgroundColor: colors.inputBg, borderColor: colors.border }]}>
          <Text style={[s.mboxT, { color: colors.text2 }]}>{message.body}</Text>
        </View>
      </View>

      {/* Analysis Details */}
      <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[s.label, { color: colors.text3 }]}>CONFIDENCE SCORE</Text>
        <ConfidenceBar confidence={result?.confidence || 0} riskLevel={riskLevel} />

        {result?.url_signals && (
          <View style={{ marginTop: 20 }}>
            <UrlAnalysis urlSignals={result.url_signals} />
          </View>
        )}

        {explanation && (
          <View style={{ marginTop: 20 }}>
            <ShapChart topSpamWords={explanation.top_spam_words} topHamWords={explanation.top_ham_words} />
          </View>
        )}

        {!explanation && !loading && (
          <View style={{ marginTop: 20, alignItems: 'center' }}>
            <ActivityIndicator size="small" color={colors.accent} />
            <Text style={[s.loadT, { color: colors.text3, fontSize: 11 }]}>Loading explanation…</Text>
          </View>
        )}
      </View>

      {/* Warning */}
      {riskLevel === 'high' && (
        <View style={[s.alert, { backgroundColor: colors.redSoft, borderColor: colors.redBorder }]}>
          <Feather name="bell" size={18} color={colors.red} />
          <View style={{ flex: 1 }}>
            <Text style={[s.alertH, { color: colors.red }]}>Immediate Action Required</Text>
            <Text style={[s.alertB, { color: colors.text2 }]}>
              Do NOT click links or share OTP / Aadhaar / bank details.{'\n\n'}
              ▸ Block the sender immediately{'\n'}
              ▸ Report at cybercrime.gov.in{'\n'}
              ▸ National Helpline: 1930
            </Text>
          </View>
        </View>
      )}

      {/* Text Signals */}
      {result?.text_signals && (
        <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Text style={[s.label, { color: colors.text3 }]}>TEXT SIGNALS</Text>
          {Object.entries(result.text_signals).map(([key, val]) => (
            <View key={key} style={s.sigRow}>
              <Text style={[s.sigKey, { color: colors.text2 }]}>{key.replace(/_/g, ' ')}</Text>
              <Text style={[s.sigVal, { color: val ? colors.red : colors.green }]}>
                {typeof val === 'boolean' ? (val ? 'Yes' : 'No') : String(val)}
              </Text>
            </View>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1 },
  content: { padding: 16, paddingBottom: 100 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  loadT: { fontSize: 13, fontWeight: '500', marginTop: 6 },
  card: { borderWidth: 1, borderRadius: 14, padding: 18, marginBottom: 14, elevation: 3 },
  verdict: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingVertical: 4 },
  verdictH: { fontSize: 18, fontWeight: '800', marginBottom: 3 },
  riskRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  rDot: { width: 7, height: 7, borderRadius: 4 },
  rLbl: { fontSize: 13, fontWeight: '500' },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  metaLabel: { fontSize: 12, fontWeight: '600', width: 65 },
  metaVal: { flex: 1, fontSize: 13, fontWeight: '600' },
  div: { borderTopWidth: 1, marginVertical: 14 },
  label: { fontSize: 10, fontWeight: '700', letterSpacing: 0.9, textTransform: 'uppercase', marginBottom: 8 },
  mbox: { borderWidth: 1, borderLeftWidth: 3, borderLeftColor: '#3b82f6', borderRadius: 10, borderTopLeftRadius: 0, borderBottomLeftRadius: 0, padding: 12 },
  mboxT: { fontSize: 13, lineHeight: 21 },
  alert: { flexDirection: 'row', gap: 12, borderWidth: 1, borderRadius: 12, padding: 16, marginBottom: 14, alignItems: 'flex-start' },
  alertH: { fontSize: 14, fontWeight: '700', marginBottom: 6 },
  alertB: { fontSize: 12, lineHeight: 20 },
  gsbBadge: { flexDirection: 'row', gap: 10, borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 14, alignItems: 'flex-start' },
  gsbTitle: { fontSize: 13, fontWeight: '700', marginBottom: 2 },
  gsbSub: { fontSize: 12, lineHeight: 18 },
  sigRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 5, borderBottomWidth: 0.5, borderBottomColor: 'rgba(128,128,128,0.15)' },
  sigKey: { fontSize: 12, textTransform: 'capitalize' },
  sigVal: { fontSize: 12, fontWeight: '700', fontVariant: ['tabular-nums'] },
});
