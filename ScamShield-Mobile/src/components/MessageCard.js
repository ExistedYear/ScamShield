import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@react-navigation/native';
import { getRiskColors } from '../utils/theme';

export default function MessageCard({ message, scanResult, onPress, onScan }) {
  const { colors } = useTheme();
  const isScanned = !!scanResult;
  const riskLevel = scanResult?.risk_level || 'low';
  const risk = getRiskColors(riskLevel, colors);

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  };

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      style={[
        styles.card,
        {
          backgroundColor: colors.surface,
          borderColor: isScanned && riskLevel !== 'low' ? risk.border : colors.border,
          shadowColor: isScanned && riskLevel === 'high' ? colors.red : '#000',
        },
      ]}
    >
      {/* Header row */}
      <View style={styles.header}>
        <View style={styles.senderRow}>
          <View
            style={[
              styles.avatar,
              {
                backgroundColor: isScanned ? risk.bg : colors.accentSoft,
                borderColor: isScanned ? risk.border : colors.accentBorder,
              },
            ]}
          >
            <Feather
              name={isScanned ? (riskLevel === 'high' ? 'alert-triangle' : riskLevel === 'medium' ? 'alert-circle' : 'check-circle') : 'message-circle'}
              size={14}
              color={isScanned ? risk.color : colors.accent}
            />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={[styles.sender, { color: colors.text }]} numberOfLines={1}>
              {message.address}
            </Text>
            <Text style={[styles.time, { color: colors.text3 }]}>{formatTime(message.date)}</Text>
          </View>
          {isScanned && (
            <View style={[styles.riskPill, { backgroundColor: risk.bg, borderColor: risk.border }]}>
              <View style={[styles.riskDot, { backgroundColor: risk.color }]} />
              <Text style={[styles.riskText, { color: risk.color }]}>
                {riskLevel === 'high' ? 'Threat' : riskLevel === 'medium' ? 'Suspicious' : 'Safe'}
              </Text>
            </View>
          )}
        </View>
      </View>

      {/* Body */}
      <Text style={[styles.body, { color: colors.text2 }]} numberOfLines={3}>
        {message.body}
      </Text>

      {/* Action row */}
      {!isScanned && onScan && (
        <TouchableOpacity
          onPress={(e) => {
            e.stopPropagation?.();
            onScan();
          }}
          style={[styles.scanBtn, { backgroundColor: colors.accent }]}
          activeOpacity={0.8}
        >
          <Feather name="shield" size={12} color="#fff" />
          <Text style={styles.scanBtnText}>Scan</Text>
        </TouchableOpacity>
      )}

      {isScanned && (
        <View style={styles.confidence}>
          <View style={[styles.confTrack, { backgroundColor: colors.surface2 }]}>
            <View
              style={[
                styles.confFill,
                {
                  backgroundColor: risk.color,
                  width: `${Math.round((scanResult?.confidence || 0) * 100)}%`,
                },
              ]}
            />
          </View>
          <Text style={[styles.confPct, { color: colors.text3 }]}>
            {Math.round((scanResult?.confidence || 0) * 100)}%
          </Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  header: {
    marginBottom: 10,
  },
  senderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  avatar: {
    width: 34,
    height: 34,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sender: {
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: -0.2,
  },
  time: {
    fontSize: 11,
    marginTop: 1,
  },
  riskPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 1,
  },
  riskDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  riskText: {
    fontSize: 11,
    fontWeight: '700',
  },
  body: {
    fontSize: 13,
    lineHeight: 20,
    marginBottom: 10,
  },
  scanBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 8,
    borderRadius: 8,
    shadowColor: '#3b82f6',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 3,
  },
  scanBtnText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: '700',
  },
  confidence: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  confTrack: {
    flex: 1,
    height: 5,
    borderRadius: 3,
    overflow: 'hidden',
  },
  confFill: {
    height: '100%',
    borderRadius: 3,
  },
  confPct: {
    fontSize: 11,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
    width: 32,
    textAlign: 'right',
  },
});
