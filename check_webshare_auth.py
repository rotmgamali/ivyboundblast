import requests
import sys

def check_auth(api_key):
    url = "https://proxy.webshare.io/api/v2/proxy/config/"
    headers = {"Authorization": f"Token {api_key}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        import json
        print(json.dumps(response.json(), indent=2))



if __name__ == "__main__":
    check_auth("b6r8obf6o6lhnqf2unozbnl1ctizrf27ubxybv48")
