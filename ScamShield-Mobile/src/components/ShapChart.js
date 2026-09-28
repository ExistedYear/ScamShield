import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@react-navigation/native';

export default function ShapChart({ topSpamWords = [], topHamWords = [] }) {
  const { colors } = useTheme();

  const allWords = [
    ...topSpamWords.map(([word, val]) => ({ word, val })),
    ...topHamWords.map(([word, val]) => ({ word, val })),
  ].sort((a, b) => Math.abs(b.val) - Math.abs(a.val));

  if (!allWords.length) return null;

  const maxVal = Math.max(...allWords.map((w) => Math.abs(w.val)));

  return (
    <View style={styles.container}>
      <Text style={[styles.title, { color: colors.text2 }]}>
        SHAP Explainability — Word Impact
      </Text>
      <View style={[styles.legend, { borderColor: colors.border }]}>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: colors.red }]} />
          <Text style={[styles.legendText, { color: colors.text3 }]}>→ Spam</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: colors.green }]} />
          <Text style={[styles.legendText, { color: colors.text3 }]}>→ Safe</Text>
        </View>
      </View>
      {allWords.slice(0, 10).map((item, i) => {
        const pct = (Math.abs(item.val) / maxVal) * 42;
        const isSpam = item.val > 0;
        return (
          <View key={i} style={styles.row}>
            <Text
              style={[styles.word, { color: colors.text2 }]}
              numberOfLines={1}
              ellipsizeMode="tail"
            >
              {item.word}
            </Text>
            <View style={styles.barContainer}>
              <View style={[styles.centerLine, { backgroundColor: colors.border }]} />
              {isSpam ? (
                <View
                  style={[
                    styles.barRight,
                    {
                      width: `${pct}%`,
                      backgroundColor: colors.red,
                    },
                  ]}
                />
              ) : (
                <View
                  style={[
                    styles.barLeft,
                    {
                      width: `${pct}%`,
                      backgroundColor: colors.green,
                    },
                  ]}
                />
              )}
            </View>
            <Text style={[styles.val, { color: colors.text3 }]}>
              {item.val > 0 ? '+' : ''}
              {item.val.toFixed(3)}
            </Text>
          </View>
        );
      })}
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
    marginBottom: 10,
  },
  legend: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 10,
    paddingBottom: 8,
    borderBottomWidth: 1,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendText: {
    fontSize: 11,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    gap: 6,
  },
  word: {
    width: 72,
    textAlign: 'right',
    fontWeight: '600',
    fontSize: 12,
  },
  barContainer: {
    flex: 1,
    height: 14,
    position: 'relative',
    justifyContent: 'center',
  },
  centerLine: {
    position: 'absolute',
    left: '50%',
    top: -1,
    bottom: -1,
    width: 1,
  },
  barRight: {
    position: 'absolute',
    left: '50%',
    height: 10,
    borderRadius: 2,
  },
  barLeft: {
    position: 'absolute',
    right: '50%',
    height: 10,
    borderRadius: 2,
  },
  val: {
    width: 50,
    fontSize: 10,
    textAlign: 'left',
  },
});
