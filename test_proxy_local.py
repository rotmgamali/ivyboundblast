import socks
import socket
import sys

def test_proxy(proxy_url):
    print(f"Testing Proxy: {proxy_url}")
    from urllib.parse import urlparse
    parts = urlparse(proxy_url)
    
    proxy_type = socks.HTTP
    host = parts.hostname
    port = parts.port
    
    s = socks.socksocket()
    s.set_proxy(proxy_type, host, port, True) # No username/password
    s.settimeout(10)
    
    try:
        print(f"Connecting to google.com:80 via {host}:{port} (HTTP IP AUTH)...")
        s.connect(("google.com", 80))
        print("✅ Proxy HTTP IP Authentication SUCCESS!")
        s.close()
    except Exception as e:
        print(f"❌ Proxy HTTP IP Authentication FAILED: {e}")

if __name__ == "__main__":
    test_proxy("http://46.203.137.27:6024")



