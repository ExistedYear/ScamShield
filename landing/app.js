/* ScamShield landing — talks to the Gradio API hosted on the HF Space.
 *
 * Set ?mock=1 (or edit MOCK below) to render against the local mock server
 * instead, so the UI can be reviewed without spending GPU quota:
 *     python3 /tmp/opencode/mock_server.py
 *     http://localhost:8000/?mock=1
 */

const PRODUCTION_API = 'https://existedyear-scamshield.hf.space';
const MOCK_API = 'http://localhost:8000';
const MOCK = new URLSearchParams(location.search).has('mock');

const API = MOCK ? MOCK_API : PRODUCTION_API;
const THRESHOLD = 0.55;

const EXAMPLES = [
  'URGENT: Your SBI account has been suspended. Verify KYC at http://sbi-kyc-verify.xyz',
  'HDFC Bank: Rs.25,000 credited to a/c XX4521. Avl bal: Rs.1,42,356. -HDFC Bank',
  'Aapka bijli connection aaj raat 9:30 baje band ho jayega. Turant call karein: 9876543210',
  'CBI notice: Aapke khilaf money laundering case darj. Digital arrest warrant. Call 9911000000.',
  'PhonePe: Rs.500 received from Rahul Kumar. UPI Ref: 4893721019.',
  'बधाई हो! आपको KBC लॉटरी में ₹25,00,000 का इनाम मिला। http://kbc-lottery.ml/win',
  'Your OTP for SBI login is 483921. Valid 10 mins. Do NOT share. -SBI',
  'Mom, I landed safely. Will call from the hotel in an hour.',
];

const SEED = [
  { s: '+91-SBI',    b: EXAMPLES[0], e: 'spam' },
  { s: '+91-VD',     b: 'CONGRATULATIONS! You have been selected as the lucky winner of Rs.5,00,000. Claim before it expires: http://prize-winner.xyz/claim', e: 'spam' },
  { s: '+91-DHL',    b: 'Your package could not be delivered. Pay Rs.2.99 customs fee at http://dhl-fee.net/track or it will be returned.', e: 'spam' },
  { s: '+91-ED',     b: 'CBI notice: Aapke khilaf money laundering case darj. Digital arrest warrant. Call 9911000000.', e: 'spam' },
  { s: '+91-MSEB',   b: 'Aapka bijli connection aaj raat 9:30 baje band ho jayega. Turant call karein: 9876543210', e: 'spam' },
  { s: '+91-PSB',    b: 'Dear user, your UPI ID expires in 24h. Renew at http://upi-renew.club/verify', e: 'spam' },
  { s: '+91-WEB',    b: 'Your account is compromised. Verify immediately at http://192.168.44.12/secure-login', e: 'spam' },
  { s: '+91-LTR',    b: 'बधाई हो! आपको KBC लॉटरी में ₹25,00,000 का इनाम मिला। http://kbc-lottery.ml/win', e: 'spam' },
  { s: '+91-UP',     b: 'प्रिय ग्राहक, आपका बिजली कनेक्शन आज रात 9:30 बजे काट दिया जाएगा। अभी कॉल करें: 9876543210', e: 'spam' },
  { s: 'HDFC-BK',   b: 'HDFC Bank: Rs.25,000 credited to a/c XX4521 on 02-May. Avl bal: Rs.1,42,356. -HDFC Bank', e: 'ham' },
  { s: 'SMS-SBI',   b: 'Your OTP for SBI Net Banking login is 483921. Valid for 10 minutes. Do not share. -SBI', e: 'ham' },
  { s: 'AIRTEL',    b: 'Airtel Thanks! Your recharge of Rs.239 is successful. Validity: 28 days. Data: 1.5GB/day. -Airtel', e: 'ham' },
  { s: 'PHONEPE',   b: 'PhonePe: Rs.500 received from Rahul Kumar. UPI Ref: 4893721019.', e: 'ham' },
  { s: 'AMAZON',    b: 'Your Amazon order #402-9876543 is out for delivery today. Track: amzn.in/track -Amazon', e: 'ham' },
  { s: 'IRCTC',     b: 'Your IRCTC ticket PNR 4567891230 is confirmed. Train 12345 on 05-May. Seat: S4/32. -IRCTC', e: 'ham' },
  { s: '+91-FAM',   b: 'Mom, I landed safely. Will call from the hotel in an hour.', e: 'ham' },
];

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/* ── Gradio client: POST to start a run, then follow the SSE stream ───────── */
async function gradioCall(apiName, args) {
  const start = await fetch(`${API}/gradio_api/call/${apiName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data: args }),
  });
  if (!start.ok) throw new Error(`API ${apiName} failed (${start.status})`);
  const { event_id } = await start.json();

  const stream = await fetch(`${API}/gradio_api/call/${apiName}/${event_id}`);
  const raw = await stream.text();

  let out = null;
  for (const line of raw.split('\n')) {
    if (!line.startsWith('data:')) continue;
    try {
      const val = JSON.parse(line.slice(5).trim());
      if (val !== null) out = val;
    } catch (_) { /* progress frames are not JSON we care about */ }
  }
  if (out === null) throw new Error(`API ${apiName} returned no data`);
  return Array.isArray(out) ? out[0] : out;
}

const predict = async (msg) => gradioCall('predict', [msg]);
const explain = async (msg) => gradioCall('explain', [msg]);

/* ── tabs ─────────────────────────────────────────────────────────────────── */
function showTab(name) {
  document.querySelectorAll('.ntab').forEach((b) =>
    b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-panel').forEach((p) =>
    p.classList.toggle('active', p.id === `panel-${name}`));
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
document.querySelectorAll('.ntab').forEach((b) =>
  b.addEventListener('click', () => showTab(b.dataset.tab)));
document.querySelectorAll('[data-goto]').forEach((b) =>
  b.addEventListener('click', () => showTab(b.dataset.goto)));

/* ── health ───────────────────────────────────────────────────────────────── */
async function ping() {
  const dot = $('#health-pill .dot-live');
  const txt = $('#health-text');
  try {
    const r = await fetch(`${API}/gradio_api/info`, { cache: 'no-store' });
    if (!r.ok) throw new Error(r.status);
    dot.classList.remove('down');
    txt.textContent = 'model live';
  } catch (_) {
    dot.classList.add('down');
    txt.textContent = 'waking up…';
  }
}

/* ── rendering ────────────────────────────────────────────────────────────── */
function riskOf(conf, level) {
  if (conf >= 0.75 || level === 'high') return ['hi', 'var(--hi)', 'High risk', '🔴'];
  if (conf >= THRESHOLD || level === 'medium') return ['md', 'var(--md)', 'Medium risk', '🟠'];
  return ['lo', 'var(--lo)', 'Low risk', '🟢'];
}

function verdictHtml(r) {
  const p = Math.round(Math.max(0, Math.min(1, r.confidence || 0)) * 100);
  const [k, colour, lvl, icon] = riskOf(r.confidence || 0, r.risk_level || '');
  const title = { spam: 'Scam detected', safe: 'Safe', ham: 'Looks legitimate' }[r.label] || 'Scam detected';

  let html = `<div class="v ${k}">
    <div class="v-top">
      <div class="v-ic ${k}">${icon}</div>
      <div>
        <div class="v-title">${title}</div>
        <div class="v-sub">${lvl} · detected as <b>${esc(r.label)}</b> · ${esc(r.language || '?')}</div>
      </div>
      <div class="v-score"><b>${p}</b><i>%</i></div>
    </div>
    <div class="meter"><div class="meter-f" style="width:${p}%;background:${colour}"></div>
      <div class="meter-t"></div></div>
    <div class="meter-s"><span>0% · ham</span><span>decision threshold 55%</span><span>100% · scam</span></div>`;

  if (r.green_channel) {
    html += `<div class="alert" style="border-color:var(--lo-b);background:var(--lo-s)">
      <b>🛡 Green Channel cleared</b> — ${esc(r.green_reason || '')}</div>`;
  }
  return html + '</div>';
}

function signalsHtml(r) {
  const u = r.url_signals || {}, t = r.text_signals || {};
  const chip = (on, label, state) =>
    `<span class="chip ${on ? 'ch-' + state : 'off'}">${label}</span>`;

  const chips = [
    chip(u.has_url, '🔗 URL present', 'md'),
    chip(u.suspicious_tld, '⚠ suspicious TLD', 'hi'),
    chip(u.has_ip_url, '🖥 raw IP host', 'hi'),
    chip(u.has_shortened_url, '🔽 shortener', 'hi'),
    chip(u.has_legit_domain, '✓ known domain', 'lo'),
    chip(u.has_http && !u.has_https, '⚠ plain HTTP', 'md'),
    chip(t.has_phone, '☎ phone number', 'md'),
    chip(t.urgency_count, `⚡ urgency ×${t.urgency_count || 0}`, (t.urgency_count || 0) >= 3 ? 'hi' : 'md'),
  ].join('');

  const rows = [
    u.has_url ? `<div class="row">🔗 <b>${u.num_urls || 0} link(s)</b> detected</div>` : '',
    `<div class="row">📏 ${t.num_chars || 0} characters · ${t.num_words || 0} tokens</div>`,
    `<div class="row mono" style="font-size:.75rem">neural <b>${(r._neural_score || 0).toFixed(3)}</b>
       · rule <b>${(r._rule_score || 0).toFixed(3)}</b>
       · ham-rule <b>${(r._ham_rule_score || 0).toFixed(3)}</b></div>`,
  ].filter(Boolean).join('');

  return `<div class="card" style="margin-top:1rem">
    <div class="card-t">Signal breakdown</div>
    <div class="chips">${chips}</div>
    <div class="rows">${rows}</div></div>`;
}

function shapHtml(ex) {
  const words = [...(ex.top_spam_words || []), ...(ex.top_ham_words || [])];
  if (!words.length) {
    return `<div class="card" style="margin-top:1rem"><div class="card-t">Why this verdict</div>
      <div class="row">No strong word-level signals for this message.</div></div>`;
  }
  const rows = words.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1])).slice(0, 12);
  const mx = Math.max(...rows.map((r) => Math.abs(r[1]))) || 1;
  const bars = rows.map(([w, v]) => {
    const pct = (Math.abs(v) / mx) * 47;
    const st = v > 0
      ? `left:50%;width:${pct}%;background:var(--hi)`
      : `right:50%;width:${pct}%;background:var(--lo)`;
    return `<div class="sh-row"><div class="sh-w">${esc(w)}</div>
      <div class="sh-t"><div class="sh-b" style="${st}"></div></div>
      <div class="sh-v">${v > 0 ? '+' : ''}${v.toFixed(3)}</div></div>`;
  }).join('');

  return `<div class="card" style="margin-top:1rem">
    <div class="card-t">Why this verdict · SHAP word impact</div>
    <div class="sh">${bars}</div>
    <div class="sh-lg">
      <span><i style="background:var(--hi)"></i>pushes toward scam</span>
      <span><i style="background:var(--lo)"></i>pushes toward legitimate</span>
    </div></div>`;
}

function warnHtml(r) {
  if (r.label !== 'spam') return '';
  return `<div class="alert">⚠ <b>Do not act on this message.</b> Never click the link or share
    your OTP, Aadhaar or bank details.<br>▸ Block the sender &nbsp;·&nbsp; ▸ Report at
    <code>cybercrime.gov.in</code> &nbsp;·&nbsp; ▸ Helpline <code>1930</code></div>`;
}

const shapPending = () => `<div class="card" style="margin-top:1rem">
  <div class="card-t">Why this verdict · SHAP word impact</div>
  <div class="row"><span class="spin"></span>Computing word attribution…</div></div>`;

/* ── scanner ──────────────────────────────────────────────────────────────── */
async function runScan() {
  const msg = $('#sms').value.trim();
  const out = $('#scan-out');
  const btn = $('#scan-btn');

  if (!msg) { $('#sms').focus(); return; }

  btn.disabled = true;
  btn.textContent = 'Scanning…';
  out.innerHTML = `<div class="card empty"><span class="spin"></span>
    <p style="margin-top:.9rem">Waiting for a GPU slot — first scan on the free tier can take ~20s.</p></div>`;

  try {
    // Verdict first, attribution after — matches how the model actually works.
    const r = await predict(msg);
    out.innerHTML = verdictHtml(r) + signalsHtml(r) + shapPending() + warnHtml(r);

    try {
      const ex = await explain(msg);
      out.innerHTML = verdictHtml(r) + signalsHtml(r) + shapHtml(ex) + warnHtml(r);
    } catch (_) {
      /* attribution is a bonus; verdict already rendered */
    }
  } catch (err) {
    out.innerHTML = `<div class="card"><div class="card-t">Scan failed</div>
      <div class="row">${esc(err.message)}<br><br>
      The model may be asleep or waiting on GPU quota — hit “Live app” in the header, or try
      again in a moment.</div></div>`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Scan message';
  }
}

/* ── mobile tab ───────────────────────────────────────────────────────────── */
const mResults = new Map();
let mCursor = 0;

function mStatsHTML(scanned, threats) {
  const safe = scanned - threats;
  const rate = scanned ? Math.round((threats / scanned) * 100) : 0;
  return `<div class="stat"><b>${scanned || '—'}</b><span>Scanned</span></div>
    <div class="stat"><b style="color:var(--hi)">${scanned ? threats : '—'}</b><span>Flagged</span></div>
    <div class="stat"><b style="color:var(--lo)">${scanned ? safe : '—'}</b><span>Safe</span></div>`;
}

function mRowHTML(seed, i, res) {
  // Same three tiers as the detail card: high → SCAM, medium → SUSPICIOUS.
  let colour = 'var(--faint)', soft = 'var(--lo-s)', brd = 'var(--lo-b)', tag = '—';
  if (res) {
    const p = Math.max(0, Math.min(1, res.confidence || 0));
    const lvl = res.risk_level || '';
    if (p >= 0.75 || lvl === 'high') {
      colour = 'var(--hi)'; soft = 'var(--hi-s)'; brd = 'var(--hi-b)'; tag = 'SCAM';
    } else if (p >= 0.55 || lvl === 'medium') {
      colour = 'var(--md)'; soft = 'var(--md-s)'; brd = 'var(--md-b)'; tag = 'SUSPICIOUS';
    } else {
      colour = 'var(--lo)'; soft = 'var(--lo-s)'; brd = 'var(--lo-b)'; tag = 'SAFE';
    }
  }
  return `<div class="in-r" data-i="${i}">
    <span class="in-d" style="background:${colour}"></span>
    <div class="in-b">
      <div class="in-s">${esc(seed.s)}</div>
      <div class="in-x">${esc(seed.b)}</div>
    </div>
    <span class="in-l" style="background:${soft};color:${colour};border:1px solid ${brd}">${tag}</span>
  </div>`;
}

function renderMobileList() {
  $('#m-list').innerHTML = SEED.map((s, i) => mRowHTML(s, i, mResults.get(i))).join('');
  $('#m-list').querySelectorAll('.in-r').forEach((el) =>
    el.addEventListener('click', () => openSeed(Number(el.dataset.i))));
}

async function scanSeed(i) {
  if (mResults.has(i)) return;
  mResults.set(i, null);
  renderMobileList();
  try {
    mResults.set(i, await predict(SEED[i].b));
  } catch (_) {
    mResults.delete(i);
  }
  renderMobileList();
}

async function scanAll() {
  const btn = $('#m-all-btn');
  btn.disabled = true;
  btn.textContent = 'Scanning…';
  for (let i = 0; i < SEED.length; i++) {
    $('#m-stats').innerHTML = mStatsHTML(i + 1, [...mResults.values()].filter((r) => r && r.label === 'spam').length);
    await scanSeed(i);
  }
  const threats = [...mResults.values()].filter((r) => r && r.label === 'spam').length;
  $('#m-stats').innerHTML = mStatsHTML(SEED.length, threats);
  btn.disabled = false;
  btn.textContent = 'Scan all';
}

async function scanNext() {
  if (mCursor >= SEED.length) mCursor = 0;
  const i = mCursor++;
  await scanSeed(i);
  openSeed(i);
}

async function openSeed(i) {
  await scanSeed(i);
  const r = mResults.get(i);
  const box = $('#m-out');
  if (!r) { box.innerHTML = ''; return; }
  let ex = null;
  try { ex = await explain(SEED[i].b); } catch (_) { /* optional */ }
  box.innerHTML = verdictHtml(r) + (ex ? shapHtml(ex) : shapPending());
}

/* ── init ─────────────────────────────────────────────────────────────────── */
function buildExamples() {
  $('#examples').innerHTML = EXAMPLES.map(
    (e) => `<button class="ex">${esc(e.length > 68 ? e.slice(0, 68) + '…' : e)}</button>`).join('');
  $('#examples').querySelectorAll('.ex').forEach((b, i) =>
    b.addEventListener('click', () => { $('#sms').value = EXAMPLES[i]; }));
}

$('#scan-btn').addEventListener('click', runScan);
$('#clear-btn').addEventListener('click', () => {
  $('#sms').value = '';
  $('#scan-out').innerHTML = `<div class="card empty"><div class="e-mark">🛡</div>
    <p>Scan a message to see the verdict, the signals behind it, and word-level attribution.</p></div>`;
});
$('#sms').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) runScan();
});
$('#m-all-btn').addEventListener('click', scanAll);
$('#m-one-btn').addEventListener('click', scanNext);

buildExamples();
renderMobileList();
$('#m-stats').innerHTML = mStatsHTML(0, 0);
ping();
setInterval(ping, 120000);