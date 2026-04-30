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
        print(f"Failed to fetch Mailreef DNS for {domain}: HTTP {resp.status_code} - Check API Key.")
        return None

def migrate_domain(domain):
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
        
    # Safety Check: Convert DMARC to p=none for warming up safely
    dmarc_val = dmarc_val.replace("p=reject", "p=none").replace("p=quarantine", "p=none")

    print(f"\nMigrating {domain} -> New MX: {mx_val}")

    # 2. Get existing Namecheap records
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
        print(f"  ❌ Namecheap Error: Your current IP ({CURRENT_IP}) must be whitelisted in Namecheap API settings.")
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
    
    # Preserve existing records but swap out Mailreef specific ones
    for host in hosts_el.findall("nc:host", namespace):
        h_name = host.get('Name')
        h_type = host.get('Type')
        h_addr = host.get('Address')
        h_ttl = host.get('TTL', '1799')
        mx_pref = host.get('MXPref', '10')

        if h_type == "MX" and h_name == "@":
            h_addr = mx_val
        elif h_type == "TXT" and h_name == "@" and "v=spf1" in h_addr:
            h_addr = spf_val
        elif h_type == "TXT" and "._domainkey" in h_name:
            h_addr = dkim_val
        elif h_type == "TXT" and h_name == "_dmarc":
            h_addr = dmarc_val
        elif h_type == "CNAME" and "errorskin" in h_addr.lower():
            # If tracking domain pointed to old server, point to new
            h_addr = mx_val 

        host_dict = {
            "HostName": h_name,
            "RecordType": h_type,
            "Address": h_addr,
            "TTL": h_ttl,
        }
        if h_type == "MX":
            host_dict["EmailType"] = "MX"
            host_dict["MXPref"] = mx_pref
            
        new_hosts.append(host_dict)

    # 3. Apply the updated records back to Namecheap
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
            set_params[f"EmailType"] = "MX"
            set_params[f"MXPref{i+1}"] = h["MXPref"]
            
    try:
        set_resp = requests.post(NC_BASE_URL, data=set_params)
        if "IsSuccess=\"true\"" in set_resp.text:
            print(f"  ✅ Successfully updated DNS records!")
        else:
            print(f"  ❌ Error setting NC hosts: {set_resp.text}")
    except Exception as e:
        print(f"  ❌ Error during setHosts: {e}")


if __name__ == "__main__":
    print(f"Starting DNS Migration using Client IP: {CURRENT_IP}")
    for domain in DOMAINS:
        migrate_domain(domain)
        time.sleep(1) # Namecheap API rate limits
    print("\n✅ All domains processed!")
