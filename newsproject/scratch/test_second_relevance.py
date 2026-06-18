import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.management.commands.fetch_indian_economy_news import is_relevant_to_india_economy

# 1. Relevant Article Mock Data (e.g. RBI rate decision details)
title_rel = "RBI Monetary Policy: Governor announces interest rate hike of 25 basis points"
full_text_rel = """
The Reserve Bank of India (RBI) Monetary Policy Committee (MPC) on Wednesday decided to increase the policy repo rate under the liquidity adjustment facility (LAF) by 25 basis points to 6.75 per cent with immediate effect.
Governor Shaktikanta Das announced that the decision was taken by a majority vote of 5 out of 6 members to keep inflation within target levels while supporting economic growth.
Economists suggest that the increase in rates will make bank loans and home mortgages more expensive, leading to a temporary cooldown in consumer borrowing.
"""

# 2. Irrelevant Article Mock Data (e.g. Sports match details)
title_irrel = "India defeats Australia by 5 wickets in dramatic cricket match"
full_text_irrel = """
India registered a stunning victory against Australia in the second ODI match of the series, chasing down a target of 285 runs with 5 wickets in hand.
KL Rahul scored a brilliant unbeaten century, anchoring the innings after a rocky start. The bowling department was led by Jasprit Bumrah who took 3 key wickets to restrict Australia.
Fans across the nation celebrated the victory as India leads the series 2-0.
"""

print("Testing RELEVANT article full text:")
res_rel = is_relevant_to_india_economy(title_rel, full_text_rel)
import json
print(json.dumps(res_rel, indent=2))

print("\nTesting IRRELEVANT article full text:")
res_irrel = is_relevant_to_india_economy(title_irrel, full_text_irrel)
print(json.dumps(res_irrel, indent=2))
