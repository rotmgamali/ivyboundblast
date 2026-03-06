import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('MAILREEF_API_KEY')
base_url = "https://api.mailreef.com"

auth = (api_key, '')

def check_endpoint(endpoint):
    print(f"Checking {endpoint}...")
    try:
        res = requests.get(f"{base_url}{endpoint}", auth=auth)
        print(f"Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

check_endpoint("/integrations")
check_endpoint("/servers")

# Also count domains again to be sure
res = requests.get(f"{base_url}/domains", auth=auth, params={"display": 1})
if res.status_code == 200:
    print(f"Total Domains Check: {res.json().get('total', 'unknown')}")
