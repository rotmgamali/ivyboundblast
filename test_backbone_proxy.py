import socks
import socket
import smtplib
import requests

def test_backbone():
    proxy_host = "p.webshare.io"
    proxy_port = 80
    user = "uyqaktdm"
    password = "q52y8plae0th"
    
    print(f"Testing Backbone Proxy {proxy_host}:{proxy_port}...")
    
    # Test HTTP connectivity first
    try:
        proxies = {
            'http': f'http://{user}:{password}@{proxy_host}:{proxy_port}',
            'https': f'http://{user}:{password}@{proxy_host}:{proxy_port}'
        }
        r = requests.get("https://api.ipify.org", proxies=proxies, timeout=10)
        print(f"✅ Backbone HTTP SUCCESS: {r.text}")
    except Exception as e:
        print(f"❌ Backbone HTTP FAILURE: {e}")

    # Test SMTP tunnel
    try:
        socks.set_default_proxy(socks.HTTP, proxy_host, proxy_port, True, user, password)
        socket.socket = socks.socksocket
        server = smtplib.SMTP_SSL("smtp.errorskin.com", 465, timeout=10)
        print("✅ Backbone SMTP SUCCESS!")
        server.quit()
    except Exception as e:
        print(f"❌ Backbone SMTP FAILURE: {e}")

if __name__ == "__main__":
    test_backbone()
