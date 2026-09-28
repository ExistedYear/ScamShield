import React, { useEffect, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { useTheme } from '@react-navigation/native';

export default function ConfidenceBar({ confidence, riskLevel }) {
  const { colors } = useTheme();
  const animatedWidth = useRef(new Animated.Value(0)).current;
  const pct = Math.round(confidence * 100);

  const barColor =
    riskLevel === 'high'
      ? colors.red
      : riskLevel === 'medium'
      ? colors.amber
      : colors.green;

  useEffect(() => {
    Animated.timing(animatedWidth, {
      toValue: pct,
      duration: 1200,
      useNativeDriver: false,
    }).start();
  }, [pct]);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={[styles.label, { color: colors.text2 }]}>Threat Confidence</Text>
        <Text style={[styles.pct, { color: colors.text }]}>{pct}%</Text>
      </View>
      <View style={[styles.track, { backgroundColor: colors.surface2, borderColor: colors.border }]}>
        <Animated.View
          style={[
            styles.fill,
            {
              backgroundColor: barColor,
              width: animatedWidth.interpolate({
                inputRange: [0, 100],
                outputRange: ['0%', '100%'],
              }),
            },
          ]}
        />
      </View>
      <View style={styles.ticks}>
        <Text style={[styles.tick, { color: colors.text3 }]}>Safe · 0%</Text>
        <Text style={[styles.tick, { color: colors.text3 }]}>Medium · 50%</Text>
        <Text style={[styles.tick, { color: colors.text3 }]}>High · 75%+</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {},
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 8,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
  },
  pct: {
    fontSize: 20,
    fontWeight: '800',
    fontVariant: ['tabular-nums'],
  },
  track: {
    height: 10,
    borderRadius: 5,
    borderWidth: 1,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 5,
  },
  ticks: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 5,
  },
  tick: {
    fontSize: 10,
  },
});
