import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@react-navigation/native';
import { getRiskColors } from '../utils/theme';

export default function RiskBadge({ riskLevel, size = 'normal' }) {
  const { colors } = useTheme();
  const risk = getRiskColors(riskLevel, colors);

  const isLarge = size === 'large';
  const boxSize = isLarge ? 56 : 36;
  const iconSize = isLarge ? 26 : 16;
  const labelSize = isLarge ? 13 : 10;

  return (
    <View style={{ alignItems: 'center', gap: isLarge ? 6 : 3 }}>
      <View
        style={[
          styles.badge,
          {
            width: boxSize,
            height: boxSize,
            borderRadius: isLarge ? 14 : 9,
            backgroundColor: risk.bg,
            borderColor: risk.border,
          },
        ]}
      >
        <Feather name={risk.icon} size={iconSize} color={risk.color} />
      </View>
      <Text
        style={[
          styles.label,
          { color: risk.color, fontSize: labelSize },
        ]}
      >
        {riskLevel === 'high' ? 'HIGH' : riskLevel === 'medium' ? 'MED' : 'SAFE'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontWeight: '800',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
  },
});
