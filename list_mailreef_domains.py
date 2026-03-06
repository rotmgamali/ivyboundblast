import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('MAILREEF_API_KEY')
base_url = "https://api.mailreef.com"

def get_all_domains():
    domains = []
    page = 1
    while True:
        try:
            res = requests.get(f"{base_url}/domains", auth=(api_key, ''), params={"page": page, "display": 100})
            if res.status_code != 200:
                print(f"Error fetching domains: {res.status_code} {res.text}")
                break
            data = res.json()
            batch = data.get('data', [])
            if not batch:
                break
            domains.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        except Exception as e:
            print(f"Exception: {e}")
            break
    return domains

print("Fetching domains...")
all_domains = get_all_domains()
print(f"Total domains found: {len(all_domains)}")

# Search for birdsgeese
birdsgeese_matches = [d for d in all_domains if "birdsgeese" in str(d).lower()]
print(f"Domains matching 'birdsgeese': {len(birdsgeese_matches)}")

# List the last 20 domains (assuming order is somewhat chronological or IDs increment)
# We'll just list the last 25 to be safe
print("\n--- Last 25 Domains (Potential new additions) ---")
for d in all_domains[-25:]:
    print(f"ID: {d.get('id')} | Name: {d.get('name')} | Status: {d.get('status')}")

# Check for server metadata if available in domain objects
print("\n--- Birdsgeese Search in Metadata ---")
for d in all_domains:
    if "birdsgeese" in str(d).lower():
        print(d)

