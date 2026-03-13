import os
import sys
import json
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())

from Jobs.researcher.serp_enricher import enrich_lead
from Jobs.content.generator import generate_pitch
from sheets_integration import GoogleSheetsClient

def scrape_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text[:10000]
    except Exception as e:
        return ""

def run_demo():
    load_dotenv()
    
    schools = [
        {"url": "https://www.buckley.org/", "city": "Sherman Oaks", "state": "CA"},
        {"url": "https://www.dalton.org/", "city": "New York", "state": "NY"},
        {"url": "https://www.lakesideschool.org/", "city": "Seattle", "state": "WA"}
    ]
    
    print("\n🎬 LIVE SYSTEM DEMO: PROCESSING 3 RANDOM LEADS\n")
    
    for item in schools:
        url = item['url']
        print(f"🔍 Analyzing: {url}...")
        
        content = scrape_url(url)
        lead = {
            "title": "New Lead Found",
            "website": url,
            "website_content": content,
            "city": item['city'],
            "state": item['state']
        }
        
        # 1. Pipeline: Enrich (Pass-through now) -> Generate (Hyper-Personalized)
        lead = enrich_lead(lead, "school")
        school_name, email, sms = generate_pitch(lead)
        
        print(f"✅ IDENTIFIED AS: {school_name}")
        print(f"📧 EMAIL PREVIEW:\n{email[:400]}...")
        print("-" * 50)

if __name__ == "__main__":
    run_demo()
