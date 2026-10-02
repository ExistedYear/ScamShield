import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@react-navigation/native';

export default function UrlAnalysis({ urlSignals }) {
  const { colors } = useTheme();

  if (!urlSignals) return null;

  const {
    has_url = 0,
    has_ip_url = 0,
    has_shortened_url = 0,
    suspicious_tld = 0,
    has_http = 0,
    has_https = 0,
    has_legit_domain = 0,
    num_urls = 0,
    max_url_len = 0,
  } = urlSignals;

  if (!has_url && num_urls === 0) return null;

  const flags = [];
  const safe = [];
  if (has_ip_url) flags.push({ text: 'IP address used instead of domain', level: 'high' });
  if (has_shortened_url) flags.push({ text: 'URL shortener detected — hides real destination', level: 'high' });
  if (suspicious_tld) flags.push({ text: 'Suspicious top-level domain (.xyz, .top, etc.)', level: 'medium' });
  if (has_http && !has_https) flags.push({ text: 'HTTP link — not encrypted, easily intercepted', level: 'medium' });
  if (num_urls > 2) flags.push({ text: `Multiple URLs found (${num_urls})`, level: 'low' });
  if (has_legit_domain) safe.push({ text: 'Verified legitimate domain detected', level: 'safe' });
  if (!flags.length && !safe.length && has_url) safe.push({ text: 'URLs present — no obvious threat signals', level: 'safe' });

  return (
    <View style={styles.container}>
      <Text style={[styles.title, { color: colors.text3 }]}>
        <Feather name="link" size={10} /> URL ANALYSIS — {num_urls || (has_url ? '1+' : '0')} LINK(S) FOUND
      </Text>
      <View style={[styles.card, { backgroundColor: colors.inputBg, borderColor: colors.border }]}>
        {flags.map((flag, i) => {
          const flagColor =
            flag.level === 'high' ? colors.red : flag.level === 'medium' ? colors.amber : colors.text2;
          return (
            <View
              key={`flag-${i}`}
              style={[styles.row, i < flags.length - 1 && { borderBottomWidth: 1, borderBottomColor: colors.border }]}
            >
              <View
                style={[
                  styles.badge,
                  {
                    backgroundColor:
                      flag.level === 'high' ? colors.redSoft : flag.level === 'medium' ? colors.amberSoft : colors.accentSoft,
                    borderColor:
                      flag.level === 'high' ? colors.redBorder : flag.level === 'medium' ? colors.amberBorder : colors.accentBorder,
                  },
                ]}
              >
                <Text style={[styles.badgeText, { color: flagColor }]}>
                  {flag.level === 'high' ? 'HIGH' : flag.level === 'medium' ? 'WARN' : 'INFO'}
                </Text>
              </View>
              <Text style={[styles.flagText, { color: colors.text2 }]}>{flag.text}</Text>
            </View>
          );
        })}
        {safe.map((item, i) => {
          const showDivider = flags.length > 0 && i === 0;
          return (
            <View
              key={`safe-${i}`}
              style={[styles.row, showDivider && { borderTopWidth: 1, borderTopColor: colors.border }]}
            >
              <View
                style={[
                  styles.badge,
                  {
                    backgroundColor: colors.greenSoft,
                    borderColor: colors.greenBorder,
                  },
                ]}
              >
                <Feather name="check-circle" size={10} color={colors.green} />
              </View>
              <Text style={[styles.flagText, { color: colors.green }]}>{item.text}</Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 4,
  },
  title: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  card: {
    borderWidth: 1,
    borderRadius: 10,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 10,
    gap: 10,
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 12,
    borderWidth: 1,
  },
  badgeText: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
  flagText: {
    flex: 1,
    fontSize: 12,
    lineHeight: 18,
  },
});
