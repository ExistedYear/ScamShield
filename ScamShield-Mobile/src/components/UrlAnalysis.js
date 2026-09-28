import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@react-navigation/native';

export default function UrlAnalysis({ urlSignals }) {
  const { colors } = useTheme();

  if (!urlSignals) return null;

  const {
    url_count = 0,
    has_url = 0,
    has_ip_url = 0,
    has_short_url = 0,
    suspicious_tld = 0,
  } = urlSignals;

  if (!has_url && url_count === 0) return null;

  const flags = [];
  if (has_ip_url) flags.push({ text: 'IP address used instead of domain', level: 'high' });
  if (has_short_url) flags.push({ text: 'URL shortener detected — hides real destination', level: 'high' });
  if (suspicious_tld) flags.push({ text: 'Suspicious top-level domain (.xyz, .top, etc.)', level: 'medium' });
  if (url_count > 2) flags.push({ text: `Multiple URLs found (${url_count})`, level: 'medium' });
  if (!flags.length && has_url) flags.push({ text: 'URLs present — exercise caution', level: 'low' });

  return (
    <View style={styles.container}>
      <Text style={[styles.title, { color: colors.text3 }]}>
        <Feather name="link" size={10} /> URL ANALYSIS — {url_count || (has_url ? '1+' : '0')} LINK(S) FOUND
      </Text>
      <View style={[styles.card, { backgroundColor: colors.inputBg, borderColor: colors.border }]}>
        {flags.map((flag, i) => {
          const flagColor =
            flag.level === 'high' ? colors.red : flag.level === 'medium' ? colors.amber : colors.text2;
          return (
            <View
              key={i}
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
