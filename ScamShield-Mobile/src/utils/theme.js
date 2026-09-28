import { DefaultTheme } from '@react-navigation/native';

/**
 * ScamShield Design System — mirrors the web UI's dark/light tokens
 *
 * React Navigation requires: { dark, colors: { primary, background, card, text, border, notification }, fonts: { ... } }
 * We extend it with our custom tokens.
 */

export const DarkTheme = {
  ...DefaultTheme,
  dark: true,
  colors: {
    ...DefaultTheme.colors,
    // React Navigation required keys
    primary: '#3b82f6',
    background: '#0d1117',
    card: '#1c2333',
    text: '#f0f6fc',
    border: '#2d3748',
    notification: '#ef4444',
    // Custom ScamShield tokens
    bg: '#0d1117',
    bg2: '#161b22',
    surface: '#1c2333',
    surface2: '#21293d',
    border2: '#3a4a60',
    accent: '#3b82f6',
    accentHover: '#2563eb',
    accentSoft: 'rgba(59,130,246,0.12)',
    accentBorder: 'rgba(59,130,246,0.35)',
    red: '#ef4444',
    redSoft: 'rgba(239,68,68,0.1)',
    redBorder: 'rgba(239,68,68,0.3)',
    green: '#22c55e',
    greenSoft: 'rgba(34,197,94,0.1)',
    greenBorder: 'rgba(34,197,94,0.3)',
    amber: '#f59e0b',
    amberSoft: 'rgba(245,158,11,0.1)',
    amberBorder: 'rgba(245,158,11,0.3)',
    text2: '#8b949e',
    text3: '#484f58',
    inputBg: '#0d1117',
  },
};

export const LightTheme = {
  ...DefaultTheme,
  dark: false,
  colors: {
    ...DefaultTheme.colors,
    // React Navigation required keys
    primary: '#2563eb',
    background: '#f6f8fa',
    card: '#ffffff',
    text: '#1f2328',
    border: '#d0d7de',
    notification: '#dc2626',
    // Custom ScamShield tokens
    bg: '#f6f8fa',
    bg2: '#ffffff',
    surface: '#ffffff',
    surface2: '#f6f8fa',
    border2: '#b1bac4',
    accent: '#2563eb',
    accentHover: '#1d4ed8',
    accentSoft: 'rgba(37,99,235,0.08)',
    accentBorder: 'rgba(37,99,235,0.25)',
    red: '#dc2626',
    redSoft: 'rgba(220,38,38,0.07)',
    redBorder: 'rgba(220,38,38,0.25)',
    green: '#16a34a',
    greenSoft: 'rgba(22,163,74,0.07)',
    greenBorder: 'rgba(22,163,74,0.25)',
    amber: '#d97706',
    amberSoft: 'rgba(217,119,6,0.07)',
    amberBorder: 'rgba(217,119,6,0.25)',
    text2: '#656d76',
    text3: '#b1bac4',
    inputBg: '#ffffff',
  },
};

/**
 * Given a risk level string, return the color set
 */
export function getRiskColors(riskLevel, colors) {
  switch (riskLevel) {
    case 'high':
      return {
        color: colors.red,
        bg: colors.redSoft,
        border: colors.redBorder,
        icon: 'alert-triangle',
      };
    case 'medium':
      return {
        color: colors.amber,
        bg: colors.amberSoft,
        border: colors.amberBorder,
        icon: 'alert-circle',
      };
    default:
      return {
        color: colors.green,
        bg: colors.greenSoft,
        border: colors.greenBorder,
        icon: 'check-circle',
      };
  }
}
