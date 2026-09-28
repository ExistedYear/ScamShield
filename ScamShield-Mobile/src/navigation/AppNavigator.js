import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '@react-navigation/native';

import HomeScreen from '../screens/HomeScreen';
import ScanScreen from '../screens/ScanScreen';
import SettingsScreen from '../screens/SettingsScreen';
import DetailScreen from '../screens/DetailScreen';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

// We pass onToggleTheme via a context to avoid render-function children
const ThemeToggleContext = React.createContext(() => {});
export { ThemeToggleContext };

function SettingsWrapper() {
  const onToggleTheme = React.useContext(ThemeToggleContext);
  return <SettingsScreen onToggleTheme={onToggleTheme} />;
}

function HomeTabs() {
  const { colors } = useTheme();

  return (
    <Tab.Navigator
      screenOptions={{
        tabBarStyle: {
          backgroundColor: colors.card,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: 64,
          paddingBottom: 8,
          paddingTop: 6,
          elevation: 0,
        },
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.text3 || colors.border,
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: '600',
        },
        headerStyle: {
          backgroundColor: colors.card,
          elevation: 0,
          shadowOpacity: 0,
          borderBottomWidth: 1,
          borderBottomColor: colors.border,
        },
        headerTintColor: colors.text,
        headerTitleStyle: {
          fontWeight: '800',
          fontSize: 17,
        },
      }}
    >
      <Tab.Screen
        name="Inbox"
        component={HomeScreen}
        options={{
          headerTitle: 'ScamShield AI',
          tabBarIcon: ({ color, size }) => <Feather name="inbox" size={size} color={color} />,
        }}
      />
      <Tab.Screen
        name="Scan"
        component={ScanScreen}
        options={{
          headerTitle: 'Threat Scanner',
          tabBarIcon: ({ color, size }) => <Feather name="shield" size={size} color={color} />,
        }}
      />
      <Tab.Screen
        name="Settings"
        component={SettingsWrapper}
        options={{
          headerTitle: 'Settings',
          tabBarIcon: ({ color, size }) => <Feather name="settings" size={size} color={color} />,
        }}
      />
    </Tab.Navigator>
  );
}

export default function AppNavigator({ onToggleTheme }) {
  const { colors } = useTheme();

  return (
    <ThemeToggleContext.Provider value={onToggleTheme}>
      <Stack.Navigator
        screenOptions={{
          headerStyle: {
            backgroundColor: colors.card,
          },
          headerTintColor: colors.text,
          headerTitleStyle: {
            fontWeight: '700',
            fontSize: 16,
          },
          headerShadowVisible: false,
          headerBackTitleVisible: false,
        }}
      >
        <Stack.Screen
          name="Main"
          component={HomeTabs}
          options={{ headerShown: false }}
        />
        <Stack.Screen
          name="Detail"
          component={DetailScreen}
          options={{ headerTitle: 'Analysis Details' }}
        />
      </Stack.Navigator>
    </ThemeToggleContext.Provider>
  );
}
