import socks
import socket
import smtplib

def test_smtp_proxy(proxy_url, target_host, target_port):
    print(f"Testing SMTP via Proxy {proxy_url} to {target_host}:{target_port}")
    try:
        from urllib.parse import urlparse
        p = urlparse(proxy_url)
        
        socks.set_default_proxy(
            socks.SOCKS5 if 'socks5' in p.scheme else socks.HTTP,
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
            
        print("✅ SUCCESS: Connection established!")
        server.quit()
    except Exception as e:
        print(f"❌ FAILURE: {e}")

if __name__ == "__main__":
    # The proxy details from the user's variables/earlier tests
    proxy = "socks5://uyqaktdm:q52y8plae0th@46.203.137.27:6024"
    
    print("--- Testing Port 465 ---")
    test_smtp_proxy(proxy, "smtp.errorskin.com", 465)
    
    print("\n--- Testing Port 587 ---")
    test_smtp_proxy(proxy, "smtp.errorskin.com", 587)
    
    print("\n--- Testing Port 80 (Control - should work) ---")
    try:
        import requests
        proxies = {'http': 'http://uyqaktdm:q52y8plae0th@46.203.137.27:6024',
                   'https': 'http://uyqaktdm:q52y8plae0th@46.203.137.27:6024'}
        r = requests.get("http://api.ipify.org", proxies=proxies, timeout=10)
        print(f"✅ Port 80 SUCCESS: {r.text}")
    except Exception as e:
        print(f"❌ Port 80 FAILURE: {e}")
