import os
import json
import sys
import requests

def probe_sent():
    api_key = os.getenv("MAILREEF_API_KEY")
    base_url = "https://api.mailreef.com"
    
    endpoints = ["/mail/sent", "/mail/outbound", "/sent", "/outbound"]
    
    for ep in endpoints:
        print(f"\nProbing {ep}...")
        try:
            response = requests.get(f"{base_url}{ep}", auth=(api_key, ''), params={"display": 5})
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"Success! Fragment: {str(data)[:500]}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    probe_sent()
