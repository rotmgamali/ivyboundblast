import os
import time
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# APIs
MR_API_KEY = os.getenv("MAILREEF_API_KEY")
NC_API_KEY = os.getenv("NAMECHEAP_API_KEY", "e97eafecae454a07a7682d29548d0177")
USERNAME = os.getenv("NAMECHEAP_USERNAME", "rollinsan23")

# Fetch local IP to pass to Namecheap, or fallback to the env one
try:
    CURRENT_IP = requests.get("https://api.ipify.org", timeout=5).text
except:
    CURRENT_IP = os.getenv("NAMECHEAP_CLIENT_IP", "136.60.140.93")

NC_BASE_URL = "https://api.namecheap.com/xml.response"
MR_BASE_URL = "https://api.mailreef.com"

DOMAINS = [
    "aspireteam.help", "aspireteam.space", "aspireteam.work",
    "aspireteamus.help", "aspireteamus.space", "aspireteamus.study",
    "aspireteamus.wiki", "aspireteamus.work", "aspireus.help",
    "aspireus.space", "aspireus.study", "aspireus.wiki", "aspireus.work",
    "aspiring.help", "aspiring.wiki", "aspiring.work", "aspiringus.help",
    "aspiringus.space", "aspiringus.study", "aspiringus.wiki", "aspiringus.work"
]

def get_mailreef_dns(domain):
    session = requests.Session()
    session.auth = (MR_API_KEY, '')
    resp = session.get(f"{MR_BASE_URL}/domains/{domain}")
    if resp.status_code == 200:
        return resp.json().get('dns', {})
    else:
        print(f"Failed to fetch Mailreef DNS for {domain}: HTTP {resp.status_code}")
        return None

def force_domain_dns(domain):
    parts = domain.split('.')
    sld, tld = parts[0], parts[1]
    
    # 1. Get New DNS records from Mailreef
    mr_dns = get_mailreef_dns(domain)
    if not mr_dns:
        return
        
    mx_val = mr_dns.get('dns_mx_pretty')
    spf_val = mr_dns.get('dns_spf_pretty')
    dkim_val = mr_dns.get('dns_dkim_pretty')
    dmarc_val = mr_dns.get('dns_dmarc_pretty')
    
    if not all([mx_val, spf_val, dkim_val, dmarc_val]):
        print(f"Missing DNS values from Mailreef for {domain}")
        return
        
    print(f"\nForcing DNS records for {domain}...")

    # 2. Get existing Namecheap records to know what to keep
    params = {
        "ApiUser": USERNAME,
        "ApiKey": NC_API_KEY,
        "UserName": USERNAME,
        "Command": "namecheap.domains.dns.getHosts",
        "ClientIp": CURRENT_IP,
        "SLD": sld,
        "TLD": tld
    }
    nc_resp = requests.get(NC_BASE_URL, params=params)
    
    if "Invalid request IP" in nc_resp.text:
        print(f"  ❌ Namecheap Error: Your current IP ({CURRENT_IP}) must be whitelisted.")
        return
        
    try:
        root = ET.fromstring(nc_resp.text)
        namespace = {'nc': 'http://api.namecheap.com/xml.response'}
        hosts_el = root.find(".//nc:DomainDNSGetHostsResult", namespace)
        
        if hosts_el is None:
            print(f"  ❌ Failed to parse Namecheap hosts for {domain}.")
            return
    except Exception as e:
        print(f"  ❌ XML Parsing error: {e}")
        return
        
    new_hosts = []
    
    # Preserve existing NON-MAIL records
    for host in hosts_el.findall("nc:host", namespace):
        h_name = host.get('Name')
        h_type = host.get('Type')
        h_addr = host.get('Address')
        h_ttl = host.get('TTL', '1799')

        # Drop old email records completely, so we don't duplicate them
        if h_type == "MX":
            continue
        if h_type == "TXT" and "v=spf1" in h_addr:
            continue
        if h_type == "TXT" and "._domainkey" in h_name:
            continue
        if h_type == "TXT" and h_name == "_dmarc":
            continue
        if h_type == "CNAME" and ("errorskin" in h_addr.lower() or "truckice" in h_addr.lower()):
            continue
            
        host_dict = {
            "HostName": h_name,
            "RecordType": h_type,
            "Address": h_addr,
            "TTL": h_ttl,
        }
        new_hosts.append(host_dict)

    # Now, explicitly APPEND exactly what Mailreef requires
    new_hosts.append({
        "HostName": "@",
        "RecordType": "MX",
        "Address": f"{mx_val}.", # Best practice to append period
        "TTL": "1799",
        "EmailType": "MX",
        "MXPref": "0" # MAILREEF STRICT CHECK REQUIRES 0
    })
    
    new_hosts.append({
        "HostName": "@",
        "RecordType": "TXT",
        "Address": spf_val,
        "TTL": "1799"
    })
    
    new_hosts.append({
        "HostName": "mail._domainkey",
        "RecordType": "TXT",
        "Address": dkim_val,
        "TTL": "1799"
    })
    
    # WARMING SAFETY: Convert DMARC to p=none during warmup to prevent
    # receiving servers from rejecting warming emails
    dmarc_val = dmarc_val.replace("p=reject", "p=none").replace("p=quarantine", "p=none")
    # Also relax sp= subdomain policy
    dmarc_val = dmarc_val.replace("sp=reject", "sp=none").replace("sp=quarantine", "sp=none")
    new_hosts.append({
        "HostName": "_dmarc",
        "RecordType": "TXT",
        "Address": dmarc_val,
        "TTL": "1799"
    })

    # 3. Apply the updated list of records back to Namecheap
    set_params = {
        "ApiUser": USERNAME,
        "ApiKey": NC_API_KEY,
        "UserName": USERNAME,
        "Command": "namecheap.domains.dns.setHosts",
        "ClientIp": CURRENT_IP,
        "SLD": sld,
        "TLD": tld
    }
    
    for i, h in enumerate(new_hosts):
        set_params[f"HostName{i+1}"] = h["HostName"]
        set_params[f"RecordType{i+1}"] = h["RecordType"]
        set_params[f"Address{i+1}"] = h["Address"]
        set_params[f"TTL{i+1}"] = h["TTL"]
        if h["RecordType"] == "MX":
            set_params[f"EmailType"] = "MX" # Require both
            set_params[f"MXPref{i+1}"] = h["MXPref"]
            
    try:
        set_resp = requests.post(NC_BASE_URL, data=set_params)
        if "IsSuccess=\"true\"" in set_resp.text:
            print(f"  ✅ Successfully forced DNS records!")
        else:
            print(f"  ❌ Error setting NC hosts: {set_resp.text}")
    except Exception as e:
        print(f"  ❌ Error during setHosts: {e}")


if __name__ == "__main__":
    print(f"Starting DNS Force utilizing Client IP: {CURRENT_IP}")
    for domain in DOMAINS:
        force_domain_dns(domain)
        time.sleep(1) # Be nice to API limits
    print("\n✅ All domains explicitly forced with new records!")
