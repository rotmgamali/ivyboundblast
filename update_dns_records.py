
import requests
import xml.etree.ElementTree as ET
import os
import time

# --- CONFIGURATION ---
API_KEY = "e97eafecae454a07a7682d29548d0177"
USERNAME = "rollinsan23"
CLIENT_IP = "136.60.140.93"  # From .env
NC_BASE_URL = "https://api.namecheap.com/xml.response"

DOMAINS = [
    "aspireteam.help", "aspireteam.space", "aspireteam.work",
    "aspireteamus.help", "aspireteamus.space", "aspireteamus.study",
    "aspireteamus.wiki", "aspireteamus.work", "aspireus.help",
    "aspireus.space", "aspireus.study", "aspireus.wiki", "aspireus.work",
    "aspiring.help", "aspiring.wiki", "aspiring.work", "aspiringus.help",
    "aspiringus.space", "aspiringus.study", "aspiringus.wiki", "aspiringus.work"
]

def update_dmarc(sld, tld):
    print(f"Checking {sld}.{tld}...")
    
    # 1. Get Existing Hosts
    try:
        params = {
            "ApiUser": USERNAME,
            "ApiKey": API_KEY,
            "UserName": USERNAME,
            "Command": "namecheap.domains.dns.getHosts",
            "ClientIp": CLIENT_IP,
            "SLD": sld,
            "TLD": tld
        }
        resp = requests.get(NC_BASE_URL, params=params)
        root = ET.fromstring(resp.text)
        
        namespace = {'nc': 'http://api.namecheap.com/xml.response'}
        hosts_el = root.find(".//nc:DomainDNSGetHostsResult", namespace)
        
        if hosts_el is None:
            print(f"  ❌ Error: Could not find DomainDNSGetHostsResult. Check API key/IP whitelist.")
            print(f"  Raw response: {resp.text[:200]}...")
            return

        new_hosts = []
        dmarc_found = False
        
        # Parse existing hosts
        for host in hosts_el.findall("nc:host", namespace):
            h_name = host.get('Name')
            h_type = host.get('Type')
            h_addr = host.get('Address')
            h_ttl = host.get('TTL')
            
            # If it's the DMARC record, update it
            if h_name == "_dmarc":
                h_addr = "v=DMARC1; p=none; rua=mailto:spam@errorskin.com;"
                dmarc_found = True
            
            new_hosts.append({
                "HostName": h_name,
                "RecordType": h_type,
                "Address": h_addr,
                "TTL": h_ttl
            })
            
        # Add DMARC if not found
        if not dmarc_found:
            new_hosts.append({
                "HostName": "_dmarc",
                "RecordType": "TXT",
                "Address": "v=DMARC1; p=none; rua=mailto:spam@errorskin.com;",
                "TTL": "1799"
            })
            
        # 2. Set Hosts (Required to send ALL hosts back)
        set_params = {
            "ApiUser": USERNAME,
            "ApiKey": API_KEY,
            "UserName": USERNAME,
            "Command": "namecheap.domains.dns.setHosts",
            "ClientIp": CLIENT_IP,
            "SLD": sld,
            "TLD": tld
        }
        
        for i, h in enumerate(new_hosts):
            set_params[f"HostName{i+1}"] = h["HostName"]
            set_params[f"RecordType{i+1}"] = h["RecordType"]
            set_params[f"Address{i+1}"] = h["Address"]
            set_params[f"TTL{i+1}"] = h["TTL"]
            
        set_resp = requests.post(NC_BASE_URL, data=set_params)
        if "IsSuccess=\"true\"" in set_resp.text:
            print(f"  ✅ Successfully updated DMARC to p=none for {sld}.{tld}")
        else:
            print(f"  ❌ Failed to update {sld}.{tld}")
            print(f"  Raw response snippet: {set_resp.text[:200]}...")
            
    except Exception as e:
        print(f"  ❌ Exception for {sld}.{tld}: {e}")

if __name__ == "__main__":
    for domain in DOMAINS:
        parts = domain.split('.')
        if len(parts) >= 2:
            sld = parts[0]
            tld = parts[1]
            update_dmarc(sld, tld)
            time.sleep(1) # Be nice to API
