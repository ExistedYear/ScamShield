#!/usr/bin/env python3
"""Test Flask API with Google Safe Browsing integration."""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smishing_detector.app.flask_api import app

def test_check_domain_endpoint():
    """Test the /check-domain endpoint."""
    client = app.test_client()
    
    print("Testing Flask /check-domain endpoint with Google Safe Browsing API...")
    print("-" * 60)
    
    test_domains = [
        ('google.com', True),
        ('amazon.com', True),
        ('paypal.com', True),
        ('github.com', True),
        ('flipkart.com', True),
        ('random-malicious-site.xyz', False),
    ]
    
    for domain, should_be_safe in test_domains:
        response = client.post(
            '/check-domain',
            data=json.dumps({'domain': domain}),
            content_type='application/json'
        )
        
        result = response.get_json()
        is_safe = result.get('is_legitimate', False)
        status_icon = "✓" if is_safe == should_be_safe else "✗"
        
        print(f"{status_icon} {domain:<35} -> {'Safe' if is_safe else 'Not Safe'}")
    
    print("-" * 60)
    print("✓ All endpoint tests complete!")
    
    # Test error handling
    print("\nTesting error handling...")
    response = client.post(
        '/check-domain',
        data=json.dumps({}),
        content_type='application/json'
    )
    if response.status_code == 400:
        print("✓ Missing domain parameter handled correctly")
    
    response = client.post(
        '/check-domain',
        data=json.dumps({'domain': ''}),
        content_type='application/json'
    )
    if response.status_code == 400:
        print("✓ Empty domain parameter handled correctly")

if __name__ == '__main__':
    test_check_domain_endpoint()
