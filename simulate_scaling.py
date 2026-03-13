import sys
import os

# Mocking the config for simulation
total_inboxes = 95
windows = [
    {"start": 6, "end": 7, "emails_per_inbox": 3},
    {"start": 7, "end": 8, "emails_per_inbox": 3},
    {"start": 8, "end": 9, "emails_per_inbox": 4},
    {"start": 9, "end": 10, "emails_per_inbox": 4},
    {"start": 10, "end": 11, "emails_per_inbox": 4},
    {"start": 12, "end": 13, "emails_per_inbox": 3},
    {"start": 15, "end": 16, "emails_per_inbox": 3},
    {"start": 16, "end": 17, "emails_per_inbox": 3},
    {"start": 17, "end": 18, "emails_per_inbox": 3},
    {"start": 18, "end": 19, "emails_per_inbox": 2},
]

def simulate_throughput():
    daily_per_inbox = sum(w["emails_per_inbox"] for w in windows)
    total_daily = daily_per_inbox * total_inboxes
    
    print(f"📊 THROUGHPUT SIMULATION")
    print(f"-------------------------")
    print(f"Total Inboxes: {total_inboxes}")
    print(f"Emails Per Inbox/Day: {daily_per_inbox}")
    print(f"TOTAL DAILY VOLUME: {total_daily}")
    
    print(f"\n⚡ SPACING AUDIT (Human Speed)")
    for w in windows:
        emails = w["emails_per_inbox"]
        interval = 60 / emails if emails > 0 else 0
        print(f"Window {w['start']:02d}:00-{w['end']:02d}:00 | {emails} emails | Spacing: {interval:.1f} mins/email")

if __name__ == "__main__":
    simulate_throughput()
