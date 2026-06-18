import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newsproject.settings')
django.setup()

from newsfeeds.management.commands.fetch_indian_economy_news import is_relevant_to_india_economy

title = "Indian Army drops colonial-era dress traditions, introduces bandi jackets in new uniform code"
desc = "The regulations permit women officers to wear sober-coloured sarees, or kurta-salwar and ankle-length straight pants with a dupatta."

print("Checking relevance of Indian Army uniform code news:")
result = is_relevant_to_india_economy(title, desc)
print("Result:")
import json
print(json.dumps(result, indent=2))
