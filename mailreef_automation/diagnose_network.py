import os
import socket
import sys

def check_connection(host, port, timeout=10, proxy_info=None):
    """Try to open a TCP connection to host:port."""
    import socket
    target_desc = f"{host}:{port}"
    if proxy_info:
        print(f"   Testing connectivity to {target_desc} via Proxy...", end='', flush=True)
    else:
        print(f"   Testing connectivity to {target_desc} (Direct)...", end='', flush=True)
        
    try:
        if proxy_info:
            import socks
            sock = socks.create_connection((host, port), timeout=timeout, **proxy_info)
        else:
            sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        print(" ✅ SUCCESS")
        return True
    except (socket.timeout, TimeoutError):
        print(" ❌ TIMEOUT")
    except ConnectionRefusedError:
        print(" ❌ REFUSED")
    except OSError as e:
        print(f" ❌ UNREACHABLE ({e})")
    except Exception as e:
        print(f" ❌ ERROR: {e}")
    return False

def run_diagnostics():
    import socket
    print("\n" + "="*50)
    print("🩺 NETWORK DIAGNOSTICS START")
    print("="*50)
    
    target_host = "smtp.errorskin.com"
    
    # Check for proxy config
    SOCKS_PROXY = os.getenv("SOCKS_PROXY_URL")
    proxy_info = None
    if SOCKS_PROXY:
        try:
            import socks
            from urllib.parse import urlparse
            
            # Use same logic as mailreef_client
            if '://' not in SOCKS_PROXY:
                url = f"http://{SOCKS_PROXY}"
            else:
                url = SOCKS_PROXY
                
            proxy_parts = urlparse(url)
            is_socks = 'socks' in proxy_parts.scheme
            
            proxy_info = {
                'proxy_type': socks.SOCKS5 if is_socks else socks.HTTP,
                'proxy_addr': proxy_parts.hostname,
                'proxy_port': proxy_parts.port or (1080 if is_socks else 80),
                'proxy_rdns': True,
                'proxy_username': proxy_parts.username,
                'proxy_password': proxy_parts.password
            }
            type_str = "SOCKS5" if is_socks else "HTTP"
            print(f"🔒 Proxy detected: [{type_str}] {proxy_info['proxy_addr']}:{proxy_info['proxy_port']}")
        except Exception as e:
            print(f"⚠️ Proxy parse error: {e}")

    # 1. Environment Check
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"📍 Container Hostname: {hostname}")
        print(f"📍 Container IP: {local_ip}")
    except Exception as e:
        print(f"⚠️ Could not get local env details: {e}")

    # 1.5 Requests Test (The most reliable check)
    if SOCKS_PROXY:
        print("\n🔍 Web Check via Proxy:")
        try:
            import requests
            proxies = {'http': SOCKS_PROXY, 'https': SOCKS_PROXY}
            # Use a longer timeout for the web check
            r = requests.get("https://api.ipify.org", proxies=proxies, timeout=15)
            print(f"   ✅ WEB PROXY SUCCESS: {r.text}")
        except Exception as e:
            # Mask the URL in the error if it contains password
            err_msg = str(e).replace(SOCKS_PROXY, "[REDACTED]")
            print(f"   ❌ WEB PROXY FAILURE: {err_msg}")


    # 2. DNS Resolution
    print(f"\n🔍 DNS Resolution: {target_host}")
    try:
        ip = socket.gethostbyname(target_host)
        print(f"   ✅ RESOLVED: {target_host} -> {ip}")
    except socket.gaierror as e:
        print(f"   ❌ DNS FAILURE: Could not resolve {target_host} ({e})")
        print("   🛑 CRITICAL: Cannot reach mail server because DNS failed.")
        print("="*50 + "\n")
        return

    # 3. Port Connectivity
    print("\n🔌 Connectivity Check:")
    print("Direct (Should fail if cloud):")
    check_connection(target_host, 465)
    check_connection(target_host, 587)
    
    if proxy_info:
        print("\nVia Proxy (Must succeed for sending):")
        # Control Test: Port 443 (Should always work if proxy is OK)
        print("--- Control Test (HTTPS) ---")
        check_connection("google.com", 443, proxy_info=proxy_info)
        
        print("\n--- SMTP Tests ---")
        check_connection(target_host, 465, proxy_info=proxy_info)
        check_connection(target_host, 587, proxy_info=proxy_info)
    else:
        print("\n⚠️ No SOCKS_PROXY_URL configured. Proxy check skipped.")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    run_diagnostics()

