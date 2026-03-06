
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

# Import the main function
from mailreef_automation.main import main

if __name__ == "__main__":
    print("🚀 Launching Strategy B (Parallel Campaign)...")
    # Set arguments to use STRATEGY_B profile
    sys.argv = [sys.argv[0], "--profile", "STRATEGY_B"]
    main()
