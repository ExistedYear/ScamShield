import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@react-navigation/native';
import { getRiskColors } from '../utils/theme';
import RiskBadge from '../components/RiskBadge';
import ConfidenceBar from '../components/ConfidenceBar';
import ShapChart from '../components/ShapChart';
import UrlAnalysis from '../components/UrlAnalysis';
import { predictSecure, predictMessage, explainMessage } from '../services/api';
import { addScanResult } from '../utils/storage';

const SCAM_TYPES = {
  'KYC / Bank Fraud': ['kyc','aadhaar','upi','account blocked','bank account','share otp'],
  'Lottery / Prize': ['prize','winner','lottery','lucky draw','won','congratulations'],
  'Digital Arrest': ['arrest','cbi','police','court','warrant','digital arrest'],
  'OTP / Phishing': ['otp','bit.ly','tinyurl','click here','verify now'],
  'Tax Scam': ['income tax','tax refund','unpaid tax','hmrc','irs'],
};

function detectTypes(text) {
  const tl = text.toLowerCase();
  return Object.entries(SCAM_TYPES)
    .filter(([, kws]) => kws.filter(k => tl.includes(k)).length >= 2)
    .map(([ty]) => ty).slice(0, 4);
}

export default function ScanScreen() {
  const { colors } = useTheme();
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState('');
  const [result, setResult] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [error, setError] = useState(null);

  const handleScan = async () => {
    if (!message.trim()) { setError('Please enter a message to analyse.'); return; }
    setError(null); setResult(null); setExplanation(null);
    setLoading(true); setPhase('Running threat analysis…');
    try {
      const pred = await predictSecure(message.trim()).catch(() => predictMessage(message.trim()));
      setResult(pred);
      await addScanResult({ messageId: `manual_${Date.now()}`, address: 'Manual Scan', body: message.trim(), ...pred });
      setPhase('Generating explainability…');
      try { const expl = await explainMessage(message.trim()); setExplanation(expl); } catch {}
    } catch (err) { setError('Failed to connect: ' + err.message); }
    setLoading(false); setPhase('');
  };

  const handleClear = () => { setMessage(''); setResult(null); setExplanation(null); setError(null); };

  const riskLevel = result?.risk_level || 'low';
  const risk = getRiskColors(riskLevel, colors);
  const threats = result ? detectTypes(message) : [];

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView style={[s.root, { backgroundColor: colors.bg }]} contentContainerStyle={s.content} keyboardShouldPersistTaps="handled">
        {/* Input */}
        <View style={[s.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Text style={[s.label, { color: colors.text3 }]}>PASTE MESSAGE, SMS OR URL</Text>
          <TextInput style={[s.input, { backgroundColor: colors.inputBg, borderColor: colors.border, color: colors.text }]}
            placeholder="Paste any suspicious content here…" placeholderTextColor={colors.text3}
            value={message} onChangeText={setMessage} multiline textAlignVertical="top" />
          <View style={s.btnRow}>
            <TouchableOpacity onPress={handleScan} style={[s.btnP, { backgroundColor: colors.accent }]} disabled={loading} activeOpacity={0.8}>
              {loading ? <ActivityIndicator size="small" color="#fff" /> : <Feather name="shield" size={14} color="#fff" />}
              <Text style={s.btnPT}>{loading ? phase : 'Run Threat Analysis'}</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={handleClear} style={[s.btnS, { borderColor: colors.border }]} activeOpacity={0.8}>
              <Feather name="x" size={14} color={colors.text2} />
            </TouchableOpacity>
          </View>
        </View>

        {error && (
          <View style={[s.err, { backgroundColor: colors.redSoft, borderColor: colors.redBorder }]}>
            <Feather name="x-circle" size={14} color={colors.red} />
            <Text style={[s.errT, { color: colors.red }]}>{error}</Text>
          </View>
        )}

        {result && (
          <View style={[s.card, { backgroundColor: colors.surface, borderColor: risk.border }]}>
            <View style={s.verdict}>
              <RiskBadge riskLevel={riskLevel} size="large" />
              <View style={{ flex: 1 }}>
                <Text style={[s.verdictH, { color: colors.text }]}>
                  {result.label === 'spam' ? 'Threat Detected' : result.label === 'safe' ? 'Verified Safe' : 'Appears Legitimate'}
                </Text>
                <View style={s.riskRow}>
                  <View style={[s.rDot, { backgroundColor: risk.color }]} />
                  <Text style={[s.rLbl, { color: colors.text2 }]}>
                    {riskLevel === 'high' ? 'High Risk' : riskLevel === 'medium' ? 'Medium Risk' : 'Low Risk'}
                  </Text>
                </View>
              </View>
              {result.language && (
                <View style={[s.langBadge, { backgroundColor: colors.accentSoft, borderColor: colors.accent }]}>
                  <Feather name="globe" size={10} color={colors.accent} />
                  <Text style={[s.langBadgeT, { color: colors.accent }]}>
                    {result.language.toUpperCase()}{result.encryption_used ? '  🔒' : ''}
                  </Text>
                </View>
              )}
            </View>

            <View style={[s.div, { borderTopColor: colors.border }]} />

            <Text style={[s.label, { color: colors.text3 }]}>SCANNED INPUT</Text>
            <View style={[s.mbox, { backgroundColor: colors.inputBg, borderColor: colors.border }]}>
              <Text style={[s.mboxT, { color: colors.text2 }]} numberOfLines={5}>{message}</Text>
            </View>

            <Text style={[s.label, { color: colors.text3, marginTop: 14 }]}>THREAT CATEGORY</Text>
            <View style={s.tagRow}>
              {threats.length > 0 ? threats.map((t, i) => (
                <View key={i} style={[s.tag, { backgroundColor: colors.redSoft, borderColor: colors.redBorder }]}>
                  <Feather name="alert-triangle" size={9} color={colors.red} />
                  <Text style={[s.tagT, { color: colors.red }]}>{t}</Text>
                </View>
              )) : (
                <View style={[s.tag, { backgroundColor: colors.greenSoft, borderColor: colors.greenBorder }]}>
                  <Feather name="check-circle" size={9} color={colors.green} />
                  <Text style={[s.tagT, { color: colors.green }]}>No known threat category</Text>
                </View>
              )}
            </View>

            {result.url_signals && <View style={{ marginTop: 14 }}><UrlAnalysis urlSignals={result.url_signals} /></View>}
            {explanation && <View style={{ marginTop: 14 }}><ShapChart topSpamWords={explanation.top_spam_words} topHamWords={explanation.top_ham_words} /></View>}

            <View style={[s.div, { borderTopColor: colors.border }]} />
            <ConfidenceBar confidence={result.confidence} riskLevel={riskLevel} />

            {riskLevel === 'high' && (
              <View style={[s.alert, { backgroundColor: colors.redSoft, borderColor: colors.redBorder }]}>
                <Feather name="bell" size={16} color={colors.red} />
                <View style={{ flex: 1 }}>
                  <Text style={[s.alertH, { color: colors.red }]}>Early Warning — Action Required</Text>
                  <Text style={[s.alertB, { color: colors.text2 }]}>
                    Do NOT click links or share OTP/Aadhaar/bank details.{'\n'}▸ Block the sender{'\n'}▸ Report at cybercrime.gov.in{'\n'}▸ Helpline: 1930
                  </Text>
                </View>
              </View>
            )}

            <TouchableOpacity onPress={handleClear} style={[s.btnS, { borderColor: colors.border, alignSelf: 'center', marginTop: 16 }]}>
              <Feather name="rotate-ccw" size={12} color={colors.text2} />
              <Text style={[s.btnST, { color: colors.text2 }]}>Scan Another</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1 },
  content: { padding: 16, paddingBottom: 100 },
  card: { borderWidth: 1, borderRadius: 14, padding: 18, marginBottom: 14, elevation: 3 },
  label: { fontSize: 10, fontWeight: '700', letterSpacing: 0.9, textTransform: 'uppercase', marginBottom: 8 },
  input: { borderWidth: 1.5, borderRadius: 10, fontSize: 14, padding: 14, minHeight: 130, lineHeight: 22 },
  btnRow: { flexDirection: 'row', gap: 10, marginTop: 14 },
  btnP: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 14, borderRadius: 10, elevation: 4 },
  btnPT: { color: '#fff', fontSize: 14, fontWeight: '700' },
  btnS: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 12, paddingHorizontal: 18, borderRadius: 10, borderWidth: 1.5 },
  btnST: { fontSize: 13, fontWeight: '600' },
  err: { flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1, borderRadius: 10, padding: 12, marginBottom: 14 },
  errT: { flex: 1, fontSize: 13, fontWeight: '500' },
  verdict: { flexDirection: 'row', alignItems: 'center', gap: 16, paddingVertical: 6 },
  verdictH: { fontSize: 17, fontWeight: '800', marginBottom: 3 },
  riskRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  rDot: { width: 7, height: 7, borderRadius: 4 },
  rLbl: { fontSize: 13, fontWeight: '500' },
  div: { borderTopWidth: 1, marginVertical: 16 },
  mbox: { borderWidth: 1, borderLeftWidth: 3, borderLeftColor: '#3b82f6', borderRadius: 10, borderTopLeftRadius: 0, borderBottomLeftRadius: 0, padding: 12, maxHeight: 100 },
  mboxT: { fontSize: 13, lineHeight: 20 },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  tag: { flexDirection: 'row', alignItems: 'center', gap: 5, borderWidth: 1, borderRadius: 20, paddingHorizontal: 10, paddingVertical: 4 },
  tagT: { fontSize: 12, fontWeight: '600' },
  alert: { flexDirection: 'row', gap: 12, borderWidth: 1, borderRadius: 12, padding: 14, marginTop: 16, alignItems: 'flex-start' },
  alertH: { fontSize: 13, fontWeight: '700', marginBottom: 6 },
  alertB: { fontSize: 12, lineHeight: 20 },
  langBadge: { flexDirection: 'row', alignItems: 'center', gap: 5, borderWidth: 1, borderRadius: 20, paddingHorizontal: 9, paddingVertical: 3, alignSelf: 'flex-start', marginTop: 6 },
  langBadgeT: { fontSize: 10, fontWeight: '700', letterSpacing: 0.5 },
});
