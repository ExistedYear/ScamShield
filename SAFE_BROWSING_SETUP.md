# Google Safe Browsing API Integration

## Summary of Changes

You've successfully replaced the hardcoded domain list with Google Safe Browsing API integration! Here's what was changed:

### Files Modified

1. **smishing_detector/utils/safe_browsing.py** (NEW)
   - New module that wraps the Google Safe Browsing API
   - Implements caching to avoid repeated API calls
   - Falls back to a hardcoded list of legitimate domains if API is unavailable
   - Includes automatic retry logic if API temporarily fails

2. **smishing_detector/utils/data_loader.py**
   - Added import for `is_domain_legitimate` from safe_browsing module
   - Updated `url_features()` function to use API instead of hardcoded LEGIT_DOMAINS set
   - Line changed: `if full_domain in LEGIT_DOMAINS:` → `if is_domain_legitimate(full_domain):`

### Key Features

✅ **Dynamic Domain Checking** - Uses Google Safe Browsing API to check domain safety in real-time
✅ **Smart Caching** - Caches results for 24 hours to reduce API calls
✅ **Fallback List** - 50+ hardcoded legitimate domains as fallback
✅ **Error Handling** - Gracefully handles API failures with automatic retry
✅ **.env File Support** - API key stored securely in `.env` (not committed to git)
✅ **New Dependency** - Added `python-dotenv` for environment variable management

## Setup

### Option 1: Using Google Safe Browsing API (Recommended)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the "Safe Browsing API"
4. Create an API key (under Credentials)
5. Set up your `.env` file:
   ```bash
   # Copy the example template
   cp .env.example .env
   
   # Edit .env and add your API key
   GOOGLE_SAFE_BROWSING_API_KEY=your-api-key-here
   ```

The `.env` file is automatically ignored by git, so your API key won't be committed.

### Option 2: Fallback Mode (No Setup Required)

If you don't set an API key in `.env`, the system will:
- Use the hardcoded list of 50+ legitimate domains
- Mark unknown domains as "not legitimate" (conservative approach)
- Still cache results to avoid repeated checks

## Testing

A test script has been created at `test_safe_browsing.py`:

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
python test_safe_browsing.py
```

## Usage in Code

The integration is automatic! When `url_features()` is called, it now uses:

```python
# Old way (hardcoded)
if full_domain in LEGIT_DOMAINS:
    has_legit_domain = 1

# New way (with API)
if is_domain_legitimate(full_domain):
    has_legit_domain = 1
```

## API Behavior

The Safe Browsing API checks domains against these threat types:
- MALWARE
- SOCIAL_ENGINEERING
- UNWANTED_SOFTWARE
- POTENTIALLY_HARMFUL_APPLICATION

A domain is marked as "legitimate" if it's **not** flagged for any of these threat types.

## Performance Impact

- **With API**: Initial call takes ~100-500ms, cached results are instant
- **Cache Size**: Default 24-hour TTL per domain
- **Rate Limiting**: Google Safe Browsing API has generous free quotas (~10,000 requests/day)

## Notes

- If API calls fail repeatedly, the system falls back to the hardcoded list
- All API calls are made synchronously in the feature extraction pipeline
- For production use, consider adding async API calls or moving to a background job
