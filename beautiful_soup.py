import json
import requests
from bs4 import BeautifulSoup



def fetch_and_parse(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        print(f"Error fetching/parsing {url}: {e}")
        return ""


def fetch_links(url):
    """
    Fetches the HTML of a webpage and extracts all hyperlinks.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract all href attributes from anchor tags
        links = [a.get('href') for a in soup.find_all('a') if a.get('href')]
        
        # Optionally, you can filter for only absolute URLs or specific patterns here
        return links
    except Exception as e:
        print(f"Error fetching/parsing {url}: {e}")
        return []

def fetch_raw_soup(url):
    # Adding a User-Agent header helps avoid getting blocked or timed out by sites like Bloomberg
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Return the unformatted/raw output of BeautifulSoup
        return str(soup)
    except Exception as e:
        return f"Error fetching/parsing {url}: {e}"

if __name__ == "__main__":
    import sys
    
    # Take link as input from command line argument
    # Example: python beautiful_soup.py "https://example.com"
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        # Prompt if no argument is passed
        target_url = input("Enter a valid URL to fetch HTML: ").strip()
        
    if target_url:
        print(f"Fetching raw HTML... Please wait.\n")
        raw_html = fetch_raw_soup(target_url)
        print(raw_html)
    else:
        print("No URL provided.")