#!/usr/bin/env python3
import sys
import os
from sheets_integration import GoogleSheetsClient
from reply_watcher import ReplyWatcher

def test_alias_logic():
    print("🧪 Testing Alias and Relaxed Filtering Logic...")
    
    # 1. Test relaxed filtering
    watcher = ReplyWatcher(profile_name="IVYBOUND")
    
    test_cases = [
        ("personal@gmail.com", "Re: Quick question about Westbridge Academy", False), # Should bypass (Subject match)
        ("random@inbox.com", "I'm interested in the SAT prep", False), # Should bypass (Default False)
        ("bot@mailreef.com", "software training", True), # Should be filtered (Generic Warmup)
        ("lead@school.edu", "Out of office", False), # Known lead email
    ]
    
    print("\n--- Filtering Test ---")
    for email, subj, expected in test_cases:
        res = watcher.is_warmup(email, subj)
        status = "PASSED" if res == expected else "FAILED"
        print(f"[{status}] Email: {email} | Subj: {subj} | Filtered: {res} (Expected: {expected})")

    # 2. Test Subject Matching
    print("\n--- Subject Matching Test ---")
    sheets = watcher.sheets_client
    
    # Simulate a reply
    reply_data = {
        'from_email': 'personal_alias@gmail.com', # NOT IN LEAD LIST
        'subject': 'Re: Supporting families at Westbridge Academy',
        'snippet': 'Hi, I saw your email about SAT prep for Westbridge.'
    }
    
    # This requires sheets.log_reply to call internal methods
    # We'll just test the internal matching logic directly for verification
    print(f"Testing enrichment for alias with subject: {reply_data['subject']}")
    
    # Mocking the enrichment logic from log_reply
    all_records = sheets._fetch_all_records()
    from_email = reply_data['from_email']
    
    # Step 1: Domain/Email Match (Will fail)
    lead = sheets._cache.get(from_email)
    print(f"1. Lead by email: {lead is not None}")
    
    # Step 2: Subject Match (Should succeed)
    reply_subject = str(reply_data.get('subject', '')).lower()
    clean_subject = reply_subject.replace('re:', '').replace('fwd:', '').strip()
    
    found_lead = None
    known_fragments = ["supporting families"]
    if any(frag in clean_subject for frag in known_fragments):
        for rec in all_records:
            if rec.get('status') in ['email_1_sent', 'email_2_sent']:
                s_name = str(rec.get('school_name', '')).lower()
                if s_name and s_name in clean_subject:
                    found_lead = rec
                    break
                    
    if found_lead:
        print(f"✅ SUCCESS: Matched alias to lead: {found_lead['email']} (School: {found_lead['school_name']})")
    else:
        print("❌ FAILED: Could not match subject to lead.")

if __name__ == "__main__":
    test_alias_logic()
