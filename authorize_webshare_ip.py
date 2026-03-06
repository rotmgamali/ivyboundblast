import requests
import sys

def authorize_ip(api_key, ip):
    url = "https://proxy.webshare.io/api/v2/proxy/ipauthorization/"
    headers = {"Authorization": f"Token {api_key}"}
    data = {"ip_address": ip}
    response = requests.post(url, headers=headers, json=data)
    print(f"Auth Response: {response.status_code}")
    print(response.json())

if __name__ == "__main__":
    authorize_ip("b6r8obf6o6lhnqf2unozbnl1ctizrf27ubxybv48", "45.115.115.117")
