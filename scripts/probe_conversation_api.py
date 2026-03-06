import os
import json
import sys
import requests

def probe_msg():
    api_key = os.getenv("MAILREEF_API_KEY")
    base_url = "https://api.mailreef.com"
    
    # Fetch one inbound message to see ALL fields
    response = requests.get(f"{base_url}/mail/inbound", auth=(api_key, ''), params={"display": 1})
    if response.status_code == 200:
        data = response.json()
        emails = data.get("data", [])
        if emails:
            msg = emails[0]
            print("KEYS IN MESSAGE OBJECT:")
            print(msg.keys())
            
            # Print specifically for conversation/thread info
            print("\nTHREAD/CONVO DATA:")
            for k in ['conversation_id', 'thread_id', 'id', 'reply_to_message_id', 'in_reply_to']:
                print(f"{k}: {msg.get(k)}")
            
            # Check if there is a way to get other messages in convo
            convo_id = msg.get('conversation_id') or msg.get('thread_id')
            if convo_id:
                 print(f"\nProbing conversation history for {convo_id}...")
                 # Try common patterns
                 for ep in [f"/mail/conversations/{convo_id}", f"/conversations/{convo_id}", f"/mail/thread/{convo_id}"]:
                     resp = requests.get(f"{base_url}{ep}", auth=(api_key, ''))
                     print(f"{ep} -> {resp.status_code}")
                     if resp.status_code == 200:
                         print("SUCCESS! Fragment:", str(resp.json())[:500])

if __name__ == "__main__":
    probe_msg()
