#!/usr/bin/env python3
import os
import requests
import json
from dotenv import load_dotenv
from mailreef_automation.mailreef_client import MailreefClient

def manual_forward():
    load_dotenv()
    api_key = os.environ.get('MAILREEF_API_KEY')
    client = MailreefClient(api_key=api_key)
    
    # 1. Get a healthy sender inbox to forward from
    inboxes = client.get_inboxes()
    if not inboxes:
        print("❌ No inboxes found to forward from.")
        return
    sender_inbox = inboxes[0]['id']
    print(f"📡 Using sender inbox: {sender_inbox}")

    recipient = 'andrew@web4guru.com'
    messages_to_forward = [
        {'email': 'hatth82@gmail.com', 'id': '63f2740268ec35FAF9'},
        {'email': 'standrewsbaystemacademy@gmail.com', 'id': '63f03b86561873FAF9'},
        {'email': 'rgrandy@academyprep.org', 'id': '63e9f36f685d33FAF9'},
        {'email': 'trilogy773@gmail.com', 'id': '63D983FAF9'}
    ]

    for item in messages_to_forward:
        print(f"Processing {item['email']}...")
        try:
            # Fetch message details to get body
            url = f"{client.base_url}/mail/inbound"
            # We already have the search results from previous step, but let's fetch individual if possible
            # Global inbound search usually works, but we need the full body.
            # I'll use the data I fetched in step 2243 which is still in memory essentially for me.
            # But for the script, I will re-fetch or use the ID to get specific message if endpoint exists.
            
            # Since I have the content from previous tool output, I will hardcode the essentials for these 4.
            # This is faster than fighting the API routes again.
            
            # Template for forwarding
            subject = f"Fwd: {item['email']} Reply"
            
            # In a real script, we'd fetch the body here.
            # I'll fetch the global inbound page 1-5 to find these messages again and get full content.
            msg_content = None
            for p in range(1, 10):
                res = client.get_global_inbound(page=p, display=100)
                for m in res.get('data', []):
                    if m.get('id') == item['id'] or m.get('from_email', '').lower() == item['email']:
                        msg_content = m
                        break
                if msg_content: break
            
            if not msg_content:
                print(f"  ✗ Message content not found for {item['email']}")
                continue

            from_addr = msg_content.get('from_email')
            date_str = msg_content.get('ts_pretty_long', 'Unknown Date')
            body_text = msg_content.get('body_text') or msg_content.get('snippet_preview')
            html_content = msg_content.get('body_html') or f"<pre>{body_text}</pre>"
            
            fwd_header = f"""
---------- Forwarded message ---------<br>
From: <b>{from_addr}</b><br>
Date: {date_str}<br>
Subject: {msg_content.get('subject_line')}<br>
To: {msg_content.get('to')[0] if msg_content.get('to') else 'unknown'}<br>
<br>
"""
            full_body_html = fwd_header + html_content
            
            # Send the "forward"
            res_send = client.send_email(
                inbox_id=sender_inbox,
                to_email=recipient,
                subject=subject,
                body=full_body_html
            )
            
            if res_send.get('status') == 'success':
                print(f"  ✓ Successfully forwarded {item['email']}")
            else:
                print(f"  ✗ Failed to send {item['email']}")
                
        except Exception as e:
            print(f"  ✗ Error {item['email']}: {e}")

if __name__ == "__main__":
    manual_forward()
