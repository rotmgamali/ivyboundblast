
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('MAILREEF_API_KEY')
base_url = "https://api.mailreef.com"
auth = (api_key, '')

domain_to_add = "web5outreach.online"
server_id = "birdsgeese"

def add_domain():
    url = f"{base_url}/domains"
    payload = {
        "name": domain_to_add,
        "server_id": server_id
    }
    
    print(f"Adding {domain_to_add} to server {server_id}...")
    try:
        res = requests.post(url, json=payload, auth=auth)
        print(f"Status: {res.status_code}")
        if res.status_code in [200, 201]:
            print("Success!")
            print(json.dumps(res.json(), indent=2))
        else:
            print(f"Failed: {res.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_domain()
