import re
import requests
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from dateutil import parser as date_parser

from newsfeeds.models import NewsArticle
from newsfeeds.spacy_utils import extract_locations_hybrid
from newsfeeds.management.commands import fetch_indian_economy_news

def read_docx_text(file_like) -> str:
    """Reads raw text from a docx file-like object using zipfile and xml parsing, with plain text fallback."""
    import io
    try:
        # Read file content into memory to support zipfile operations reliably on Django file uploads
        file_bytes = file_like.read()
        if not file_bytes:
            raise ValueError("Uploaded file is empty (0 bytes). Please make sure you have saved content inside it.")
            
        if hasattr(file_like, 'seek'):
            file_like.seek(0)
            
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            # Extract text paragraph-by-paragraph to preserve lines and prevent split-run layout issues
            paragraphs = []
            for p_node in root.findall('.//w:p', namespaces):
                p_text = "".join(node.text for node in p_node.findall('.//w:t', namespaces) if node.text)
                if p_text.strip():
                    paragraphs.append(p_text.strip())
            return "\n".join(paragraphs)
    except Exception as e:
        # Fallback: if the file is not a zip file, it might be a plain text file with a .docx extension
        try:
            decoded_text = file_bytes.decode('utf-8', errors='ignore')
            if "title:" in decoded_text.lower():
                return decoded_text
        except Exception:
            pass
        raise ValueError(f"Failed to parse docx format: {e}")

def parse_manual_content(text_content: str) -> dict:
    """Parses a text block containing fields like title, link, description, source, published_date."""
    fields = {}
    
    # Normalise newlines and strip leading/trailing whitespaces on each line
    text_content = text_content.replace('\r\n', '\n').replace('\r', '\n')
    text_content = '\n'.join(line.strip() for line in text_content.splitlines())
    
    # Patterns to look for (case-insensitive, followed by colon)
    patterns = {
        'title': r'(?:^|\n)title\s*:\s*(.*?)(?=\n(?:title|link|description|discription|source|published_date|published\s*date|date)\s*:|$)',
        'link': r'(?:^|\n)link\s*:\s*(.*?)(?=\n(?:title|link|description|discription|source|published_date|published\s*date|date)\s*:|$)',
        'description': r'(?:^|\n)(?:description|discription)\s*:\s*(.*?)(?=\n(?:title|link|description|discription|source|published_date|published\s*date|date)\s*:|$)',
        'source': r'(?:^|\n)source\s*:\s*(.*?)(?=\n(?:title|link|description|discription|source|published_date|published\s*date|date)\s*:|$)',
        'published_date': r'(?:^|\n)(?:published_date|published\s*date|date)\s*:\s*(.*?)(?=\n(?:title|link|description|discription|source|published_date|published\s*date|date)\s*:|$)'
    }
    
    for field_name, pattern in patterns.items():
        match = re.search(pattern, text_content, re.IGNORECASE | re.DOTALL)
        if match:
            fields[field_name] = match.group(1).strip()
        else:
            fields[field_name] = ""
            
    return fields

def parse_multiple_manual_contents(text_content: str) -> list:
    """Splits a text block containing multiple news articles and parses each one."""
    # Normalise newlines and strip leading/trailing whitespaces on each line
    text_content = text_content.replace('\r\n', '\n').replace('\r', '\n')
    text_content = '\n'.join(line.strip() for line in text_content.splitlines())
    
    # Split by occurrences of "title:" on its own line or after a newline/start of text.
    # We use a lookahead to split right before each "title:" prefix.
    segments = re.split(r'(?=(?:^|\n)title\s*:)', text_content, flags=re.IGNORECASE)
    
    parsed_articles = []
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        parsed = parse_manual_content(segment)
        if parsed.get('title'):
            parsed_articles.append(parsed)
            
    # Fallback if splitting didn't produce anything but the original text has a title
    if not parsed_articles and text_content.strip():
        parsed = parse_manual_content(text_content)
        if parsed.get('title'):
            parsed_articles.append(parsed)
            
    return parsed_articles

def process_manual_article(art: dict, save_to_db: bool = False) -> dict:
    """Runs the full Indian economy classification & analysis pipeline on a manual article."""
    try:
        r = requests.get("http://localhost:11434/", timeout=0.5)
        fetch_indian_economy_news.OLLAMA_AVAILABLE = (r.status_code == 200)
    except Exception:
        fetch_indian_economy_news.OLLAMA_AVAILABLE = False

    if not fetch_indian_economy_news.OLLAMA_AVAILABLE:
        raise ConnectionError("Ollama is not running. Please start the Ollama service before running manual analysis.")

    title = art.get('title', '').strip()
    link = art.get('link', '').strip()
    description = art.get('description', '').strip()
    source = art.get('source', '').strip() or 'Economic News'
    published_date_str = art.get('published_date', '').strip()

    if not title:
        raise ValueError("Title is required for manual analysis.")

    # Parse date safely
    try:
        if published_date_str:
            dt = date_parser.parse(published_date_str)
        else:
            dt = datetime.now()
    except Exception:
        dt = datetime.now()

    # Make timezone aware
    try:
        dt_aware = make_aware(dt)
    except Exception:
        dt_aware = dt

    # 2. Run Relevance Filtering
    relevance_result = fetch_indian_economy_news.is_relevant_to_india_economy(title, description)
    
    # 3. Generate Summary / Insight
    summary = fetch_indian_economy_news.generate_summary(title, description, "")
    
    # 4. Classification (L1, Sector, L2 sub_type, Channel)
    classification = fetch_indian_economy_news.classify_article_with_ollama(title, description, "")
    
    event_class_val = classification.get('event_class', 'Macro_Economy') or 'Macro_Economy'
    sector_val = classification.get('sector', 'General / Macro') or 'General / Macro'
    
    # Check for general/macro classification and blank them out
    event_class_lower = event_class_val.lower()
    sector_lower = sector_val.lower()
    is_general = (
        "macro" in event_class_lower or
        "general" in event_class_lower or
        "macro" in sector_lower or
        "general" in sector_lower
    )
    
    if any(w in event_class_val.lower() for w in ("macro", "general")):
        event_class_val = ""
    if any(w in sector_val.lower() for w in ("macro", "general")):
        sector_val = ""
    
    # 5. Direction & Impact Score
    direction_result = fetch_indian_economy_news.analyze_direction_from_india_view(title, description, summary)
    
    # 6. Origin Identification
    try:
        res_origin = extract_locations_hybrid(title, description, "")
        origin = res_origin.get("origin", "Global")
    except Exception:
        origin = "Global"

    analysis_data = {
        'title': title,
        'link': link or '#',
        'source': source,
        'published_date': dt_aware.isoformat() if hasattr(dt_aware, 'isoformat') else str(dt_aware),
        'description': description,
        'summary': summary,
        'reason': relevance_result.get('reason', ''),
        'matched_keywords': relevance_result.get('matched_keywords', []),
        'is_relevant': False,
        
        # Taxonomy
        'event_class': event_class_val,
        'sector': sector_val,
        'sub_type': classification.get('sub_type', 'General_Terms (General)'),
        'channel': classification.get('channel', 'Macroeconomic Transmission'),
        
        # Sentiment
        'direction': direction_result.get('direction', 'neutral'),
        'impact_score': direction_result.get('impact_score', 0),
        'direction_reason': direction_result.get('reason', ''),
        
        # Origin
        'origin': origin
    }

    if not save_to_db:
        return {
            "status": "success",
            "saved": False,
            "article": analysis_data
        }

    # 7. Save/Update in Django database
    if is_general:
        return {
            "status": "skipped_general",
            "saved": False,
            "reason": f"Skipped saving due to general classification (Event Class: {classification.get('event_class')}, Sector: {classification.get('sector')}).",
            "article": analysis_data
        }

    # Test to avoid duplicate news (check if title, link, and date all match an existing entry in DB)
    if NewsArticle.objects.filter(
        title=title,
        link=link or '#',
        published_date=dt_aware
    ).exists():
        from newsfeeds.models import DuplicateNewsArticle
        article_obj = DuplicateNewsArticle.objects.create(
            title=title,
            link=link or '#',
            source=source,
            published_date=dt_aware,
            description=description,
            full_text=description,
            summary=summary,
            reason=relevance_result.get('reason', ''),
            matched_keywords=relevance_result.get('matched_keywords', []),
            is_relevant=False,
            event_class=event_class_val,
            sector=sector_val,
            sub_type=classification.get('sub_type', 'General_Terms (General)'),
            channel=classification.get('channel', 'Macroeconomic Transmission'),
            direction=direction_result.get('direction', 'neutral'),
            impact_score=direction_result.get('impact_score', 0),
            direction_reason=direction_result.get('reason', ''),
            origin=origin
        )
        return {
            "status": "saved_as_duplicate",
            "saved": True,
            "reason": "Article already exists in main NewsArticle table, saved to DuplicateNewsArticle table.",
            "article": {
                "id": article_obj.id,
                "title": article_obj.title,
                "sector": article_obj.sector,
                "event_class": article_obj.event_class,
                "sub_type": article_obj.sub_type,
                "direction": article_obj.direction,
                "origin": article_obj.origin,
            }
        }

    article_obj, created = NewsArticle.objects.update_or_create(
        title=title,
        link=link or '#',
        published_date=dt_aware,
        defaults={
            'source': source,
            'description': description,
            'full_text': description,
            'summary': summary,
            'reason': relevance_result.get('reason', ''),
            'matched_keywords': relevance_result.get('matched_keywords', []),
            'is_relevant': False,
            
            # Taxonomy
            'event_class': event_class_val,
            'sector': sector_val,
            'sub_type': classification.get('sub_type', 'General_Terms (General)'),
            'channel': classification.get('channel', 'Macroeconomic Transmission'),
            
            # Sentiment
            'direction': direction_result.get('direction', 'neutral'),
            'impact_score': direction_result.get('impact_score', 0),
            'direction_reason': direction_result.get('reason', ''),
            
            # Origin
            'origin': origin
        }
    )

    return {
        "status": "success",
        "saved": True,
        "created": created,
        "article": {
            "id": article_obj.id,
            "title": article_obj.title,
            "sector": article_obj.sector,
            "event_class": article_obj.event_class,
            "sub_type": article_obj.sub_type,
            "direction": article_obj.direction,
            "origin": article_obj.origin,
        }
    }

class Command(BaseCommand):
    help = "Manually parse and analyze a news article."
    
    def add_arguments(self, parser):
        parser.add_argument('--text', type=str, help='Raw text contents to parse and analyze.')
        
    def handle(self, *args, **options):
        # Check if local Ollama is running
        try:
            r = requests.get("http://localhost:11434/", timeout=0.5)
            ollama_running = (r.status_code == 200)
        except Exception:
            ollama_running = False
            
        if not ollama_running:
            self.stderr.write("CRITICAL ERROR: local Ollama is not running! Please start the Ollama service before running manual analysis.")
            import sys
            sys.exit(1)

        text = options.get('text')
        if not text:
            self.stderr.write("Please provide text using --text")
            return
        
        parsed = parse_manual_content(text)
        self.stdout.write(f"Parsed fields: {parsed}")
        
        try:
            res = process_manual_article(parsed)
            self.stdout.write(f"SUCCESS: {res}")
        except Exception as e:
            self.stderr.write(f"ERROR: {e}")
