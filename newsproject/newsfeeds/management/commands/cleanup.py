import re
from django.core.management.base import BaseCommand
from newsfeeds.models import NewsArticle

def clean_generated_text(text: str) -> str:
    if not text:
        return text
        
    # Remove leading conversational sentences ending with a colon
    text = re.sub(r"^(Here is|Here's|Here are|Based on|This article|In this|A short).*?:\s*", "", text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove leading conversational sentences ending with a newline
    text = re.sub(r"^(Here is|Here's|Here are).*?(summary|overview|options).*?\n+", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"^(Based on the).*?\n+", "", text, flags=re.IGNORECASE | re.DOTALL)
    
    # If the LLM still provided "Option 1... Option 2...", extract just Option 1
    match = re.search(r"Option 1.*?:\s*\"?(.*?)\"?(?=\s*Option 2|$)", text, flags=re.IGNORECASE | re.DOTALL)
    if match:
        text = match.group(1).strip()
        
    # Strip trailing questions
    text = re.sub(r"(Would you like|Do you want|Let me know if).*?\?$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
    
    return text.strip()

class Command(BaseCommand):
    help = 'Cleans up existing database summaries using the robust cleanup function'

    def handle(self, *args, **options):
        self.stdout.write("Starting database cleanup...")
        count = 0
        for article in NewsArticle.objects.all():
            original = article.summary
            content = clean_generated_text(original)
            
            if content != original:
                article.summary = content
                article.save()
                count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully cleaned {count} articles.'))
