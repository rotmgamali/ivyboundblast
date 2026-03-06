while kill -0 75011 2>/dev/null; do sleep 10; done; python3 reply_watcher.py --daemon > mailreef_automation/logs/reply_watcher_final.log 2>&1 &
