"""Google Safe Browsing API integration for domain legitimacy checking."""

import os
import time
import requests
from typing import Optional, Dict
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


# Google Safe Browsing API v4 endpoint
SAFE_BROWSING_API_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

# Threat types to check for
THREAT_TYPES = ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"]

# Platform types - use ANY_PLATFORM to check all platforms
PLATFORM_TYPES = ["ANY_PLATFORM"]


class SafeBrowsingChecker:
    """Wrapper for Google Safe Browsing API with caching and fallback logic."""
    
    def __init__(self):
        """Initialize the Safe Browsing checker."""
        self.api_key = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY")
        self.cache: Dict[str, str] = {}  # domain -> known_safe | known_malicious | unknown
        self.cache_timestamps: Dict[str, float] = {}  # domain -> timestamp
        self.cache_ttl = 86400  # 24 hours in seconds
        self.api_available = True
        self.last_api_check = time.time()
        self.fallback_legit_domains = {
            'amazon.com', 'amazon.co.uk', 'amazon.in', 'netflix.com', 'spotify.com', 'apple.com',
            'google.com', 'microsoft.com', 'paypal.com', 'ebay.com', 'walmart.com',
            'target.com', 'bestbuy.com', 'costco.com', 'fedex.com', 'ups.com', 'usps.com',
            'airlines.com', 'ba.com', 'united.com', 'delta.com', 'jetblue.com',
            'library.org', 'cvs.com', 'walgreens.com', 'riteaid.com', 'shopify.com',
            'slack.com', 'zoom.us', 'gmail.com', 'outlook.com', 'yahoo.com',
            'flipkart.com', 'myntra.com', 'swiggy.com', 'zomato.com', 'makemytrip.com', 'yatra.com',
            'cleartrip.com', 'paytm.com', 'phonepe.com', 'hdfcbank.com', 'onlinesbi.sbi', 'icicibank.com',
            'axisbank.com', 'kotak.com', 'airindia.in', 'goindigo.in', 'irctc.co.in', 'redbus.in',
            'olacabs.com', 'hotstar.com', 'sonyliv.com', 'zee5.com', 'jiocinema.com',
            'timesofindia.indiatimes.com', 'hindustantimes.com', 'thehindu.com', 'ndtv.com', 'moneycontrol.com',
            'bseindia.com', 'nseindia.com', 'naukri.com', 'shaadi.com', 'bharatmatrimony.com',
            'bookmyshow.com', 'policybazaar.com', 'nykaa.com', 'ajio.com', 'firstcry.com',
            'bigbasket.com', 'blinkit.com', 'zepto.com', 'upstox.com', 'groww.in', 'zerodha.com',
            'airtel.in', 'jio.com', 'myvi.in', 'vi.com', 'bsnl.co.in', 'tataplay.com', 'dishtv.in',
            'sbicard.com', 'bajajfinserv.in', 'cred.club',
            # Tech/Development domains
            'github.com', 'gitlab.com', 'bitbucket.org', 'stackoverflow.com', 'developer.mozilla.org',
            'npm.com', 'pypi.org', 'docker.com', 'heroku.com', 'aws.amazon.com',
            'azure.microsoft.com', 'gcp.google.com', 'atlassian.com', 'jira.com', 'confluence.com'
        }
    
    def _is_cache_valid(self, domain: str) -> bool:
        """Check if cached result is still valid."""
        if domain not in self.cache_timestamps:
            return False
        return (time.time() - self.cache_timestamps[domain]) < self.cache_ttl
    
    def _check_safe_browsing_api(self, domain: str) -> Optional[str]:
        """
        Query Google Safe Browsing API for known threats.
        Returns known_malicious if threats are found, unknown if no match exists,
        and None if the API could not be queried.
        """
        if not self.api_key:
            return None
        
        try:
            payload = {
                "client": {
                    "clientId": "smishing-detector",
                    "clientVersion": "1.0"
                },
                "threatInfo": {
                    "threatTypes": THREAT_TYPES,
                    "platformTypes": PLATFORM_TYPES,
                    "threatEntries": [
                        {"url": f"http://{domain}"},
                        {"url": f"https://{domain}"}
                    ]
                }
            }
            
            response = requests.post(
                f"{SAFE_BROWSING_API_URL}?key={self.api_key}",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("matches"):
                    return "known_malicious"
                # Safe Browsing is a blocklist. No match means "not known bad",
                # not proof that a new phishing domain is legitimate.
                return "unknown"
            else:
                # Log the error response for debugging
                error_msg = f"Safe Browsing API returned {response.status_code} for {domain}"
                try:
                    error_details = response.json()
                    error_msg += f": {error_details}"
                except:
                    error_msg += f": {response.text}"
                print(error_msg)
                
                # API error - mark API as unavailable for a while
                self.api_available = False
                self.last_api_check = time.time()
                return None
                
        except requests.exceptions.Timeout:
            print(f"Safe Browsing API timeout for {domain}")
            self.api_available = False
            self.last_api_check = time.time()
            return None
        except Exception as e:
            print(f"Safe Browsing API error for {domain}: {e}")
            return None
    
    def is_domain_legitimate(self, domain: str) -> bool:
        """
        Check if a domain is legitimate using Google Safe Browsing API.
        Falls back to cached hardcoded domains if API is unavailable.
        
        Args:
            domain: Domain name to check (e.g., 'google.com')
            
        Returns:
            True if domain appears safe, False otherwise
        """
        # Normalize domain
        domain = domain.lower().strip()
        
        # Check cache first
        if domain in self.cache and self._is_cache_valid(domain):
            return self.cache[domain] == "known_safe"
        
        # Check hardcoded fallback list (always trust these)
        if domain in self.fallback_legit_domains:
            self.cache[domain] = "known_safe"
            self.cache_timestamps[domain] = time.time()
            return True
        
        # Try API if available - will detect known malicious domains
        if self.api_available or (time.time() - self.last_api_check) > 300:  # Retry every 5 minutes
            result = self._check_safe_browsing_api(domain)
            if result is not None:
                # result=True means GSB found NO threats → domain is safe
                # result=False means GSB found threats → domain is dangerous
                self.cache[domain] = result
                self.cache_timestamps[domain] = time.time()
                return self.cache[domain] == "known_safe"

        # API unavailable — conservatively treat unknown domains as not legitimate
        self.cache[domain] = "unknown"
        self.cache_timestamps[domain] = time.time()
        return False
    
    def check_domain_status(self, domain: str) -> str:
        """Return known_safe, known_malicious, or unknown for a domain."""
        domain = domain.lower().strip()
        self.is_domain_legitimate(domain)
        return self.cache.get(domain, "unknown")

    def clear_cache(self):
        """Clear the domain cache."""
        self.cache.clear()
        self.cache_timestamps.clear()


# Global instance
_checker = None


def get_checker() -> SafeBrowsingChecker:
    """Get the global Safe Browsing checker instance."""
    global _checker
    if _checker is None:
        _checker = SafeBrowsingChecker()
    return _checker


def is_domain_legitimate(domain: str) -> bool:
    """
    Check if a domain is legitimate using Google Safe Browsing API.
    
    Args:
        domain: Domain name to check (e.g., 'google.com')
        
    Returns:
        True if domain appears safe, False otherwise
    """
    return get_checker().is_domain_legitimate(domain)


def check_domain_status(domain: str) -> str:
    """Return known_safe, known_malicious, or unknown for a domain."""
    return get_checker().check_domain_status(domain)


def clear_domain_cache():
    """Clear the domain legitimacy cache."""
    get_checker().clear_cache()
