import re

def clean_geotext(text: str) -> str:
    if not text:
        return ""
    # Remove standard URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove google news base64 patterns (e.g. CBMi...)
    text = re.sub(r'[A-Za-z0-9+/]{15,}=?\d*', '', text)
    # Remove any parameters like /articles/CBMi...
    text = re.sub(r'articles/[A-Za-z0-9+/=]+', '', text)
    return text.strip()

def main():
    description = '<a href="https://news.google.com/rss/articles/CBMilAFBVV95cUxQaXRnNXJsRkFlT3hEMnZIMWMzQm01MEtXX2lZZ3MtQjRISjV6eHdXWW9FaHhBMjV2M3JTby15R0pPVTA4Z283ekJRVkpUbVJaUzhTMnE3S3VqWDBPQ040emw4UkduRVVhdDRJQnp2Z1JxdjJxblg0NDR2ekNiMHp2OGFwcGFBSkVWT0NJdG9VQTJqYk02?oc=5" target="_blank">Coinbase offers trading using Indian rupee</a>&nbsp;&nbsp;<font color="#6f6f6f">Reuters</font>'
    
    print("Original description:")
    print(description)
    print("\nCleaned description:")
    print(repr(clean_geotext(description)))

if __name__ == '__main__':
    main()
