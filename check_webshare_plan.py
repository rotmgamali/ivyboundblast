import requests
import sys

def check_plan(api_key):
    url = "https://proxy.webshare.io/api/v2/plan/"
    headers = {"Authorization": f"Token {api_key}"}
    response = requests.get(url, headers=headers)
    print(f"Plan Response: {response.status_code}")
    if response.status_code == 200:
        import json
        print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    check_plan("b6r8obf6o6lhnqf2unozbnl1ctizrf27ubxybv48")
