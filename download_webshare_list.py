import requests
import sys

def download_list(token):
    # Try text format for raw strings
    url = f"https://proxy.webshare.io/api/v2/proxy/list/download/{token}/-/-/username/password//"
    print(f"Downloading from: {url}")
    response = requests.get(url)
    print(f"Response: {response.status_code}")
    if response.status_code == 200:
        print("--- PROXY LIST START ---")
        print(response.text)
        print("--- PROXY LIST END ---")

if __name__ == "__main__":
    download_list("hxinrsbtpahvlbkhutzlzlsmizglvlabxoasfvgh")
