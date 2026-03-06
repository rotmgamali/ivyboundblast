import requests
import sys

def get_proxy(api_key):
    url = "https://proxy.webshare.io/api/v2/proxy/list/"
    headers = {"Authorization": f"Token {api_key}"}
    # Try direct mode first to see specific IPs
    response = requests.get(url, headers=headers, params={"mode": "direct"})
    
    if response.status_code == 200:
        data = response.json()
        proxies = data.get('results', [])
        for p in proxies:
            if p.get('proxy_address') == '46.203.137.27':
                print(f"DEBUG: Full Proxy Data: {p}")
            print(f"socks5://{p['username']}:{p['password']}@{p['proxy_address']}:{p['port']} (SOCKS5 field: {p.get('socks5_port')})")
        if not proxies:
            print("No proxies found in your account.")
    else:
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        get_proxy(sys.argv[1])
    else:
        print("Usage: python3 script.py <API_KEY>")
