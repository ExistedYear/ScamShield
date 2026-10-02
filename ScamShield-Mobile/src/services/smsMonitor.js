/**
 * Android SMS monitoring for ScamShield.
 *
 * The current app uses inbox polling because Expo background tasks cannot
 * install a true SMS BroadcastReceiver by themselves. Foreground polling runs
 * while the app is open; background polling is scheduled by Android and may
 * run less often depending on battery and OEM policy.
 */

import { PermissionsAndroid, Platform, NativeModules } from 'react-native';
import * as BackgroundFetch from 'expo-background-fetch';
import * as TaskManager from 'expo-task-manager';
import * as Notifications from 'expo-notifications';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { initEncryption, predictSecure, setBaseUrl } from './api';
import { addScanResult, getSettings } from '../utils/storage';

const LAST_SEEN_KEY = 'scamshield_last_sms_date';
const SMS_LIMIT = 30;
export const MONITOR_TASK = 'SCAMSHIELD_SMS_MONITOR';
export const smsLog = [];
const MAX_LOG = 50;

function _log(msg) {
  const entry = `[${new Date().toLocaleTimeString('en-IN')}] ${msg}`;
  smsLog.unshift(entry);
  if (smsLog.length > MAX_LOG) smsLog.pop();
  console.log('[ScamShield]', msg);
}

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

async function configureApiFromSettings() {
  const settings = await getSettings();
  if (settings.apiUrl) setBaseUrl(settings.apiUrl);
  await initEncryption();
  return settings;
}

async function requestNotificationPermission() {
  const { status } = await Notifications.requestPermissionsAsync();
  return status === 'granted';
}

export async function requestSmsPermission() {
  if (Platform.OS !== 'android') return false;

  const result = await PermissionsAndroid.requestMultiple([
    PermissionsAndroid.PERMISSIONS.READ_SMS,
    PermissionsAndroid.PERMISSIONS.RECEIVE_SMS,
  ]);

  return result[PermissionsAndroid.PERMISSIONS.READ_SMS] === PermissionsAndroid.RESULTS.GRANTED;
}

async function sendThreatNotification(address, body, confidence) {
  await Notifications.scheduleNotificationAsync({
    content: {
      title: 'ScamShield: Suspicious SMS Detected',
      body: `From ${address}: "${body.slice(0, 80)}..."`,
      subtitle: `Confidence: ${Math.round(confidence * 100)}%`,
      data: { address, body },
    },
    trigger: null,
  });
}

export function readInboxSms(count = SMS_LIMIT) {
  return new Promise((resolve) => {
    if (Platform.OS !== 'android') {
      _log('readInboxSms skipped — not Android');
      resolve([]);
      return;
    }

    (async () => {
      try {
        const granted = await requestSmsPermission();
        if (!granted) {
          _log('readInboxSms — SMS permission denied');
          resolve([]);
          return;
        }

        _log('readInboxSms calling native module...');
        const raw = await NativeModules.SmsReaderModule.readSms(count);
        _log('readInboxSms got ' + raw.length + ' messages');
        const messages = raw.map((sms) => ({
          id: String(sms._id),
          address: sms.address,
          body: sms.body,
          date: parseInt(sms.date, 10),
          read: sms.read === 1,
        }));
        resolve(messages);
      } catch (err) {
        _log('readInboxSms ERROR: ' + err.message);
        resolve([]);
      }
    })();
  });
}

async function getNewMessages() {
  const lastSeen = parseInt(await AsyncStorage.getItem(LAST_SEEN_KEY) || '0', 10);
  const all = await readInboxSms(SMS_LIMIT);
  return all.filter((m) => m.date > lastSeen);
}

async function markSeen(messages) {
  if (!messages.length) return;
  const latest = Math.max(...messages.map((m) => m.date));
  await AsyncStorage.setItem(LAST_SEEN_KEY, String(latest));
}

export async function scanNewMessages({ notify = true } = {}) {
  const settings = await configureApiFromSettings();
  const newMsgs = await getNewMessages();

  if (!newMsgs.length) {
    _log('scanNewMessages — 0 new msgs');
    return { scanned: 0, threats: 0 };
  }

  _log('scanNewMessages — ' + newMsgs.length + ' new, scanning...');

  let threats = 0;
  for (const msg of newMsgs) {
    try {
      const result = await predictSecure(msg.body);
      const scanData = { messageId: msg.id, address: msg.address, body: msg.body, ...result };
      await addScanResult(scanData);

      const risky = result.label === 'spam' && (result.risk_level === 'high' || result.risk_level === 'medium');
      if (risky) {
        threats += 1;
        if (notify && settings.notifications !== false) {
          await sendThreatNotification(msg.address, msg.body, result.confidence);
        }
      }
    } catch (_) {
      // skip this message, continue with next
    }
  }

  await markSeen(newMsgs);
  return { scanned: newMsgs.length, threats };
}

TaskManager.defineTask(MONITOR_TASK, async () => {
  try {
    const result = await scanNewMessages({ notify: true });
    return result.scanned > 0
      ? BackgroundFetch.BackgroundFetchResult.NewData
      : BackgroundFetch.BackgroundFetchResult.NoData;
  } catch (_) {
    return BackgroundFetch.BackgroundFetchResult.Failed;
  }
});

export async function startMonitoring() {
  try {
    const smsGranted = await requestSmsPermission();
    if (!smsGranted) {
      return { ok: false, reason: 'SMS permission was not granted.' };
    }

    await requestNotificationPermission();
    await configureApiFromSettings();

    const status = await BackgroundFetch.getStatusAsync();
    if (status === BackgroundFetch.BackgroundFetchStatus.Restricted ||
        status === BackgroundFetch.BackgroundFetchStatus.Denied) {
      return { ok: false, reason: 'Background fetch is not available on this device.' };
    }

    const registered = await TaskManager.isTaskRegisteredAsync(MONITOR_TASK);
    if (!registered) {
      await BackgroundFetch.registerTaskAsync(MONITOR_TASK, {
        minimumInterval: 15 * 60,
        stopOnTerminate: false,
        startOnBoot: true,
      });
    }

    return { ok: true };
  } catch (err) {
    return { ok: false, reason: err.message };
  }
}

export async function stopMonitoring() {
  try {
    await BackgroundFetch.unregisterTaskAsync(MONITOR_TASK);
  } catch (_) {}
}

export async function isMonitoring() {
  return TaskManager.isTaskRegisteredAsync(MONITOR_TASK);
}

const DEMO_MESSAGES = [
  { id: '1', address: '+91-98765-43210', body: 'URGENT: Your SBI account has been suspended due to KYC verification failure. Update immediately at http://sbi-kyc-verify.xyz/update or your account will be blocked within 24 hours.', date: Date.now() - 300000, read: false },
  { id: '2', address: 'AD-HDFCBK', body: 'Dear Customer, your HDFC Bank a/c ending 4521 credited Rs.25,000.00 on 28-May. Avl bal: Rs.1,42,356.80. - HDFC Bank', date: Date.now() - 600000, read: true },
  { id: '3', address: '+1-555-0199', body: 'Congratulations! You have been selected as the lucky winner of our $50,000 prize draw! Claim: http://prize-claim.top/winner?id=382912', date: Date.now() - 900000, read: false },
  { id: '4', address: 'VM-PAYTMB', body: 'Your Paytm order #ORD8834521 has been shipped! Track: https://paytm.com/track/ORD8834521. Estimated delivery: 30 May.', date: Date.now() - 1200000, read: true },
  { id: '5', address: '+91-87654-00000', body: 'Aapka electricity connection aaj raat 9:30 PM tak band ho jayega. Turant call karein Officer Sharma: 9876543210', date: Date.now() - 1500000, read: false },
  { id: '6', address: 'JD-AMAZON', body: 'Your Amazon order of "USB-C Cable" has been delivered. Rate your experience: https://amazon.in/review/B0943XK', date: Date.now() - 1800000, read: true },
  { id: '7', address: '+91-99000-11111', body: 'Dear user, your UPI ID is about to expire. Renew at http://upi-renew.club/verify and enter your OTP. Failure will deactivate your UPI.', date: Date.now() - 2100000, read: false },
  { id: '8', address: 'AD-AIRTEL', body: 'Airtel Thanks! Your recharge of Rs.239 is successful. Validity: 28 days. Data: 1.5GB/day. - Airtel', date: Date.now() - 2400000, read: true },
];

export function getDemoMessages() {
  return [...DEMO_MESSAGES].sort((a, b) => b.date - a.date);
}

export function simulateIncomingSms() {
  const scams = [
    // ── English (5) ──────────────────────────────────────────────────────────
    { address: '+91-70001-11111', body: 'URGENT: Your SBI account has been suspended due to KYC failure. Verify immediately at http://sbi-kyc-verify.xyz/update or funds will be frozen.' },
    { address: 'VM-PRIZE', body: 'Congratulations! You have won Rs.10,00,000 in the Amazon lucky draw. Claim your prize now: http://amazon-prize.xyz/claim' },
    { address: '+1-555-0199', body: 'Your package delivery failed. Pay customs clearance fee of Rs.299 at http://dhl-customs.top/fee or parcel will be returned to sender.' },
    { address: 'HP-INCOME', body: 'Income Tax Department: Tax refund of Rs.15,420 is pending. Verify your bank account at http://incometax-refund.in/claim within 24 hours.' },
    { address: '+91-99000-22222', body: 'Your PAN card has been deactivated by the IT department. Reactivate now at http://pan-reactivate.online/verify or face legal consequences.' },

    // ── Hindi (5) ────────────────────────────────────────────────────────────
    { address: '+91-87654-11111', body: 'प्रिय ग्राहक, आपका बिजली कनेक्शन आज रात 9:30 बजे काट दिया जाएगा। तुरंत कॉल करें: 9876543210' },
    { address: 'VM-SBIHI', body: 'आपके बैंक खाते में संदिग्ध गतिविधि पाई गई है। KYC अपडेट करें: http://sbi-kyc-update.xyz/verify नहीं तो खाता ब्लॉक हो जाएगा।' },
    { address: '+91-76543-22222', body: 'बधाई हो! आपको KBC लॉटरी में ₹25,00,000 का इनाम मिला है। दावा करें: http://kbc-lottery.ml/win' },
    { address: 'HP-CBIHI', body: 'CBI सूचना: आपके खिलाफ मनी लॉन्ड्रिंग का केस दर्ज है। डिजिटल अरेस्ट वारंट जारी। बचने के लिए संपर्क करें: 9911000000' },
    { address: '+91-65432-33333', body: 'आपका आधार कार्ड 24 घंटे में ब्लॉक हो जाएगा। रिएक्टिवेट करें: http://uidai-secure.tk/update' },

    // ── Hinglish (5) ─────────────────────────────────────────────────────────
    { address: '+91-88765-11111', body: 'Dear customer, aapka electricity connection aaj raat 9:30 baje band ho jayega. Turant bill pay karein nahi to permanent cut ho jayega. Call: 9876543210' },
    { address: 'AD-CBIBK', body: 'CBI ALERT: Aapke naam pe money laundering case darj hua hai. Digital arrest warrant jaari hone wala hai. Turant officer se sampark karein: 9911000000' },
    { address: '+91-77654-22222', body: 'Aapka SBI bank khata suspend ho gaya hai KYC incomplete hone ki wajah se. Abhi verify karein: http://sbi-update.xyz/kyc warna aapke paise freeze ho jayenge.' },
    { address: 'HP-LOTTO', body: 'Badhai ho! Aapne Rs.50,00,000 ka inaam jeeta hai humaare lucky draw mein. Claim karne ke liye turant link pe click karein: http://prize-claim.ml/winner' },
    { address: '+91-66543-33333', body: 'Aapka Aadhaar card block hone wala hai. 24 ghante mein verify karein: http://uidai-verify.xyz/update nahi to aapki sabhi government services band ho jayengi.' },
  ];
  const t = scams[Math.floor(Math.random() * scams.length)];
  return { id: `sim_${Date.now()}`, ...t, date: Date.now(), read: false };
}
