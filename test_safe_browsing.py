#!/usr/bin/env python3
"""Test script for Google Safe Browsing API integration."""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smishing_detector.utils.safe_browsing import is_domain_legitimate, get_checker, clear_domain_cache


def test_safe_browsing():
    """Test the Safe Browsing API integration."""
    
    test_domains = [
        # Known safe domains
        ('google.com', True),
        ('amazon.com', True),
        ('paypal.com', True),
        ('github.com', True),
        
        # Fallback hardcoded safe domains
        ('flipkart.com', True),
        ('netflix.com', True),
        
        # Unknown domains (will likely be marked as not legitimate without API key)
        ('random-unknown-domain-xyz.com', False),
        ('potentially-malicious-domain.net', False),
    ]
    
    print("Testing Safe Browsing API integration...")
    print("-" * 60)
    
    api_key = os.getenv("GOOGLE_SAFE_BROWSING_API_KEY")
    if not api_key:
        print("⚠️  WARNING: GOOGLE_SAFE_BROWSING_API_KEY environment variable not set")
        print("   Using fallback hardcoded domains only\n")
    else:
        print("✓ API Key found - will use Google Safe Browsing API\n")
    
    checker = get_checker()
    
    for domain, expected_safe in test_domains:
        result = is_domain_legitimate(domain)
        status = "✓" if result == expected_safe else "✗"
        
        print(f"{status} {domain:<40} -> {'Safe' if result else 'Not Safe'}")
    
    print("-" * 60)
    print(f"Cache stats: {len(checker.cache)} domains cached")
    
    print("\n✓ Test complete!")
    print("\nNote: If you want to use the full Google Safe Browsing API:")
    print("1. Go to https://console.cloud.google.com/")
    print("2. Create a new project")
    print("3. Enable the Safe Browsing API")
    print("4. Create an API key")
    print("5. Copy .env.example to .env and add your API key:")
    print("   cp .env.example .env")
    print("   # Then edit .env and paste your API key")


if __name__ == '__main__':
    test_safe_browsing()
