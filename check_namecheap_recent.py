
import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

API_USER = os.getenv("NAMECHEAP_USERNAME")
API_KEY = os.getenv("NAMECHEAP_API_KEY")
CLIENT_IP = os.getenv("NAMECHEAP_CLIENT_IP")
# Using sandbox or production? User gave real key likely. Production URL.
API_URL = "https://api.namecheap.com/xml.response"

def get_recent_domains():
    if not API_USER or not API_KEY or not CLIENT_IP:
        print("Error: Missing credentials")
        return []

    # Command: namecheap.domains.getList
    # Sort by CREATED
    params = {
        "ApiUser": API_USER,
        "ApiKey": API_KEY,
        "UserName": API_USER,
        "Command": "namecheap.domains.getList",
        "ClientIp": CLIENT_IP,
        "PageSize": 20,
        "SortBy": "CREATED", # or CREATEDDATE if that's the key
        # Actual key is likely "CREATED" based on docs, or we fetch all (100) and sort in python
        # Let's try fetching 100 and sort python side to be safe as API sorting can be finicky
        "PageSize": 100
    }
    
    try:
        r = requests.get(API_URL, params=params)
        if r.status_code != 200:
            print(f"Error: {r.status_code} {r.text}")
            return []
        
        # Parse XML
        root = ET.fromstring(r.text)
        ns = {'nc': 'http://api.namecheap.com/xml.response'}
        
        # Check errors
        errors = root.findall(".//{http://api.namecheap.com/xml.response}Errors/*")
        if errors:
            print("API Errors:")
            for e in errors:
                print(f"- {e.text}")
            return []
            
        domains = []
        # Namespace handling for ElementTree can be annoying.
        # Let's iterate all elements to find Domain
        for elem in root.iter():
            # Tag will be {http://api.namecheap.com/xml.response}Domain
            if elem.tag.endswith("Domain"): 
                # Attributes: ID, Name, User, Created, Expires, IsExpired, IsLocked, AutoRenew, WhoisGuard, IsPremium, IsOurDNS
                d = {
                    "Name": elem.attrib.get("Name"),
                    "Created": elem.attrib.get("Created"),
                    "ID": elem.attrib.get("ID")
                }
                domains.append(d)
                
        # Sort by Created DESC in Python
        domains.sort(key=lambda x: x["Created"], reverse=True)
        
        if not domains:
            print(f"DEBUG: No domains parsed. Raw Response:\n{r.text[:500]}...") # Print first 500 chars
            
        return domains[:20]
        
    except Exception as e:
        print(f"Exception: {e}")
        return []

if __name__ == "__main__":
    recent = get_recent_domains()
    print(f"Found {len(recent)} domains.")
    for i, d in enumerate(recent):
        print(f"{i+1}. {d['Name']} (Created: {d['Created']})")
