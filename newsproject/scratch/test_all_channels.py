import sys
import os
from pathlib import Path

# Add directories to python path so we can run outside of Django environment if needed, 
# or use Django configuration.
sys.path.insert(0, str(Path(__file__).parent.parent))

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newsproject.settings")
django.setup()

from newsfeeds.management.commands.channel_maps import CHANNEL_MAP, CHANNELS
from newsfeeds.management.commands.fetch_indian_economy_news import get_channels_from_mapper

def run_all_tests():
    print("=" * 100)
    print("RUNNING COMPREHENSIVE CHANNEL MAPPING TEST FOR ALL SUBTYPES")
    print("=" * 100)
    
    passed_count = 0
    total_count = len(CHANNEL_MAP)
    
    for (event_class, subtype), expected_channel_ids in sorted(CHANNEL_MAP.items()):
        # Convert expected channel IDs to names
        expected_names = sorted([CHANNELS[cid].channel_name for cid in expected_channel_ids])
        
        # Test how get_channels_from_mapper resolves the event_class and subtype
        resolved_names = get_channels_from_mapper(event_class, subtype)
        resolved_names = sorted(resolved_names)
        
        status = "SUCCESS" if resolved_names == expected_names else "MISMATCH / FALLBACK"
        if status == "SUCCESS":
            passed_count += 1
            
        print(f"L1: {event_class:<20} | L2: {subtype:<30}")
        print(f"  Expected: {', '.join(expected_names)}")
        print(f"  Resolved: {', '.join(resolved_names) if resolved_names else '[None]'}")
        print(f"  Status  : {status}")
        print("-" * 100)
        
    print(f"\nTest Summary: {passed_count}/{total_count} resolved successfully.")
    print("=" * 100)

if __name__ == "__main__":
    run_all_tests()
