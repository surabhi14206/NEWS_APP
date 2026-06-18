import requests
from bs4 import BeautifulSoup
import trafilatura
import urllib.parse

def search_duckduckgo(query: str, num_results: int = 15) -> list[str]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    encoded_query = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
    
    print(f"Searching: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Search HTTP Status: {response.status_code}")
        if response.status_code != 200:
            return []
            
        soup = BeautifulSoup(response.content, 'html.parser')
        links = []
        
        # Look for result link anchors
        for a in soup.find_all('a', class_='result__snippet'):
            href = a.get('href')
            if href:
                # Resolve redirect if needed
                if href.startswith('//duckduckgo.com/l/?kh='):
                    # Parse the redirect URL
                    parsed = urllib.parse.urlparse(href)
                    qd = urllib.parse.parse_qs(parsed.query)
                    if 'uddg' in qd:
                        href = qd['uddg'][0]
                links.append(href)
            if len(links) >= num_results:
                break
                
        # Backup selector if result__snippet doesn't work
        if not links:
            for a in soup.find_all('a', class_='result__url'):
                href = a.get('href')
                if href:
                    if href.startswith('//duckduckgo.com/l/?kh='):
                        parsed = urllib.parse.urlparse(href)
                        qd = urllib.parse.parse_qs(parsed.query)
                        if 'uddg' in qd:
                            href = qd['uddg'][0]
                    links.append(href.strip())
                if len(links) >= num_results:
                    break
        return links
    except Exception as e:
        print(f"Error searching DDG: {e}")
        return []

def fetch_content(url: str) -> str:
    print(f"Attempting to fetch content from: {url}")
    try:
        # Fetch using requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            extracted = trafilatura.extract(downloaded)
            if extracted and len(extracted.strip()) > 200:
                return extracted.strip()
        
        # Fallback to requests + bs4 if trafilatura fails
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            # remove script/style tags
            for s in soup(['script', 'style', 'nav', 'footer', 'header']):
                s.decompose()
            text = soup.get_text(separator=' ', strip=True)
            if len(text) > 200:
                return text
        return ""
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

if __name__ == "__main__":
    query = "Stocks Pressured by AI Selloff and Jump in Oil Prices"
    links = search_duckduckgo(query, 10)
    print(f"Found {len(links)} links:")
    for i, l in enumerate(links, 1):
        print(f"{i}. {l}")
        
    print("\n--- Starting Scrape Test ---")
    scraped_text = ""
    for i, url in enumerate(links, 1):
        print(f"\nResult {i}:")
        text = fetch_content(url)
        if text:
            print(f"SUCCESS! Scraped {len(text)} characters.")
            print("Preview:")
            print(text[:300] + "...")
            scraped_text = text
            break
        else:
            print(f"FAILED to scrape Result {i}. Trying next...")
            
    if not scraped_text:
        print("\nAll top search results failed to scrape.")
