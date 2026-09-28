# ScamShield Mobile — SMS Smishing Detector

A cross-platform mobile app built with **React Native (Expo)** that scans incoming SMS messages in real-time using the ScamShield AI smishing detection API.

## Features

- 📨 **SMS Inbox Scanner** — View all SMS messages with risk indicators
- 🔍 **Manual Scanner** — Paste any message/URL for analysis  
- 🧠 **AI-Powered Detection** — DistilBERT + hand-crafted features model
- 📊 **SHAP Explainability** — See which words triggered the detection
- 🔗 **URL Safety Checks** — Google Safe Browsing API integration
- 🌙 **Dark/Light Theme** — Matches the ScamShield web UI design
- ⚙️ **Configurable** — API URL, auto-scan, notification toggles

## Prerequisites

- **Node.js** ≥ 18
- **Expo CLI** — `npm install -g expo-cli`
- **Flask API** running (from `../smishing_detector/`)

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npx expo start

# Run on Android (requires emulator or device)
npx expo start --android

# Run on web (for preview)
npx expo start --web
```

## Connect to API

1. Start the Flask API:
   ```bash
   cd ../smishing_detector
   python -m app.flask_api
   ```
2. In the app, go to **Settings** → enter your API server URL  
   - Same WiFi: `http://<your-local-ip>:5000`  
   - Deployed: `https://your-server.com`

## Build APK

```bash
# Install EAS CLI
npm install -g eas-cli

# Log in to Expo
eas login

# Build APK (preview profile)
eas build --platform android --profile preview

# Build production APK
eas build --platform android --profile production
```

## Project Structure

```
ScamShield-Mobile/
├── App.js                          # Root with theme + navigation
├── app.json                        # Expo config
├── eas.json                        # EAS Build config (APK)
├── src/
│   ├── components/
│   │   ├── ConfidenceBar.js        # Animated threat confidence bar
│   │   ├── MessageCard.js          # SMS card with risk badge
│   │   ├── RiskBadge.js            # Color-coded risk indicator
│   │   ├── ShapChart.js            # SHAP word-impact chart
│   │   └── UrlAnalysis.js          # URL safety breakdown
│   ├── navigation/
│   │   └── AppNavigator.js         # Tab + stack navigation
│   ├── screens/
│   │   ├── HomeScreen.js           # SMS inbox dashboard
│   │   ├── ScanScreen.js           # Manual message scanner
│   │   ├── DetailScreen.js         # Full analysis view
│   │   └── SettingsScreen.js       # App configuration
│   ├── services/
│   │   ├── api.js                  # Flask API client
│   │   └── smsListener.js          # SMS inbox reader
│   └── utils/
│       ├── storage.js              # AsyncStorage helpers
│       └── theme.js                # Design system tokens
```

## API Endpoints Used

| Endpoint | Method | Purpose |
|---|---|---|
| `/predict` | POST | Classify message as spam/ham |
| `/explain` | POST | SHAP explainability |
| `/check-domain` | POST | Google Safe Browsing lookup |
| `/health` | GET | API health check |
| `/batch_predict` | POST | Batch classification |
