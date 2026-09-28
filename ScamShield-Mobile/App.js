import React, { useState, useEffect, useCallback } from 'react';
import { StatusBar } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import AppNavigator from './src/navigation/AppNavigator';
import { DarkTheme, LightTheme } from './src/utils/theme';
import { setBaseUrl } from './src/services/api';
import { getSettings } from './src/utils/storage';

export default function App() {
  const [isDark, setIsDark] = useState(true);

  useEffect(() => {
    // Load saved theme preference and API URL
    (async () => {
      try {
        const settings = await getSettings();
        if (settings.darkMode !== undefined) setIsDark(settings.darkMode);
        if (settings.apiUrl) setBaseUrl(settings.apiUrl);
      } catch {}
    })();
  }, []);

  const toggleTheme = useCallback(async () => {
    const next = !isDark;
    setIsDark(next);
    try {
      const settings = await getSettings();
      settings.darkMode = next;
      await AsyncStorage.setItem('@scamshield_settings', JSON.stringify(settings));
    } catch {}
  }, [isDark]);

  const theme = isDark ? DarkTheme : LightTheme;

  return (
    <NavigationContainer theme={theme}>
      <StatusBar
        barStyle={isDark ? 'light-content' : 'dark-content'}
        backgroundColor={theme.colors.bg}
      />
      <AppNavigator onToggleTheme={toggleTheme} />
    </NavigationContainer>
  );
}
