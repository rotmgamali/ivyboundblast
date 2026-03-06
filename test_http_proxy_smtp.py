import socks
import socket
import smtplib

def test_smtp_http_proxy(proxy_url, target_host, target_port):
    print(f"Testing SMTP via HTTP Proxy {proxy_url} to {target_host}:{target_port}")
    try:
        from urllib.parse import urlparse
        p = urlparse(proxy_url)
        
        # Use socks.HTTP instead of socks.SOCKS5
        socks.set_default_proxy(
            socks.HTTP,
            p.hostname,
            p.port,
            True,
            p.username,
            p.password
        )
        socket.socket = socks.socksocket
        
        print("Initial socket set. Attempting connection...")
        
        if target_port == 465:
            server = smtplib.SMTP_SSL(target_host, target_port, timeout=10)
        else:
            server = smtplib.SMTP(target_host, target_port, timeout=10)
            server.starttls()
            
        print("✅ SUCCESS: Connection established over HTTP Proxy!")
        server.quit()
    except Exception as e:
        print(f"❌ FAILURE: {e}")

if __name__ == "__main__":
    # Note: Using http scheme and Port 6024
    proxy = "http://uyqaktdm:q52y8plae0th@46.203.137.27:6024"
    
    print("--- Testing Port 465 via HTTP ---")
    test_smtp_http_proxy(proxy, "smtp.errorskin.com", 465)
    
    print("\n--- Testing Port 587 via HTTP ---")
    test_smtp_http_proxy(proxy, "smtp.errorskin.com", 587)
    
    print("\n--- Testing Port 443 (Control - should work) ---")
    try:
        import requests
        proxies = {'http': proxy, 'https': proxy}
        r = requests.get("https://api.ipify.org", proxies=proxies, timeout=10)
        print(f"✅ Port 443 SUCCESS: {r.text}")
    except Exception as e:
        print(f"❌ Port 443 FAILURE: {e}")
