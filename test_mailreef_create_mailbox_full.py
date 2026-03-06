
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('MAILREEF_API_KEY')
base_url = "https://api.mailreef.com"
auth = (api_key, '')

email_to_add = "andrew@web5outreach.online" # Derived from domain + slug usually
# actually payload usually requires 'email' OR 'slug'+'domain'
# The error said missing: server, domain, display_name, slug, tags
# So I should provide them all.

server_id = "birdsgeese"
domain_name = "web5outreach.online"

def add_mailbox_full():
    url = f"{base_url}/mailboxes"
    payload = {
        "email": f"andrew@{domain_name}", # Optional if slug/domain provided?
        "server": server_id,
        "domain": domain_name,
        "display_name": "Andrew",
        "slug": "andrew",
        "tags": ["strategy_b"]
    }
    
    print(f"Adding mailbox full payload for {domain_name}...")
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
    add_mailbox_full()
