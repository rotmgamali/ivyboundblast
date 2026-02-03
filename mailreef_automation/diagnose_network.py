import socket
import sys

def check_connection(host, port, timeout=5):
    """Try to open a TCP connection to host:port."""
    print(f"   Testing connectivity to {host}:{port}...", end='', flush=True)
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        print(" ✅ SUCCESS")
        return True
    except socket.timeout:
        print(" ❌ TIMEOUT")
    except ConnectionRefusedError:
        print(" ❌ REFUSED")
    except OSError as e:
        print(f" ❌ UNREACHABLE ({e})")
    except Exception as e:
        print(f" ❌ ERROR: {e}")
    return False

def run_diagnostics():
    print("\n" + "="*50)
    print("🩺 NETWORK DIAGNOSTICS START")
    print("="*50)

    target_host = "smtp.errorskin.com"
    
    # 1. Environment Check
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"📍 Container Hostname: {hostname}")
        print(f"📍 Container IP: {local_ip}")
    except Exception as e:
        print(f"⚠️ Could not get local env details: {e}")

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
    port_465 = check_connection(target_host, 465)
    port_587 = check_connection(target_host, 587)
    
    # Summary
    print("\n📝 Result:")
    if port_465 or port_587:
        print("   ✅ Mail server is REACHABLE on at least one port.")
    else:
        print("   ❌ Mail server is UNREACHABLE on standard SMTP ports.")
        print("      Likely Cause: Cloud Firewall (Egress Block) or IP Blacklist.")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    run_diagnostics()
