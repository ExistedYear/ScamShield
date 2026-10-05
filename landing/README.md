# ScamShield — landing site

Static front end for ScamShield. Calls the Gradio JSON API on the Hugging Face
Space; no model runs in the browser and nothing is built here.

```
landing/
├── index.html   markup for all four tabs
├── styles.css   design tokens + component styles
├── app.js       Gradio SSE client, rendering, tab logic
└── scamshield.apk   (drop the Android build here)
```

## Point it at an API

The endpoint lives at the top of `app.js`:

```js
const PRODUCTION_API = 'https://existedyear-scamshield.hf.space';
const MOCK_API = 'http://localhost:8000';
const MOCK = new URLSearchParams(location.search).has('mock');
const API = MOCK ? MOCK_API : PRODUCTION_API;
```

Append `?mock=1` to render against a local mock server — useful for styling work
without spending GPU quota.

## Local preview

```bash
cd landing && python3 -m http.server 8080
# → http://localhost:8080
```

Plain static hosting, so any of these work:
`python3 -m http.server` · `npx serve` · deploy straight to Vercel / Netlify /
Cloudflare Pages / GitHub Pages.

## Deploy

Vercel picks this folder up automatically. From the repo root:

```bash
npx vercel            # preview
npx vercel --prod     # production
```

`vercel.json` in the repo root points the build output at `landing/`, so
deploying the repo root works without configuring anything in the dashboard.
