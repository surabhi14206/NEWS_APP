# Scraping Output Files - Complete Guide

## 📁 Output File Structure

After running `python manage.py fetch_indian_economy_news`, you'll get these output files with **SCRAPED CONTENT**:

### 1. **newsfeeds_scrape_log.json** (Main Log)
- **Location:** `c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\newsproject\`
- **Contains:** Full detailed pipeline log with all articles
- **Key Sections:**
  - `fetched_rss_feeds` - Raw RSS feed data
  - `selected_articles` - ✅ **Selected articles with FULL SCRAPED CONTENT**
  - `rejected_articles` - Articles rejected at various stages
  - `all_articles_log` - Complete pipeline history for each article

```json
{
  "selected_articles": [
    {
      "title": "...",
      "scraped_content": "FULL TEXT HERE (thousands of characters)",
      "summary_generated": "AI-generated summary",
      "analysis": {
        "taxonomy": {...},
        "direction": {...},
        "trade_share": "...",
        "origin": "..."
      }
    }
  ]
}
```

---

### 2. **articles_with_scraped_content.csv** (Summary Table)
- **Location:** `Outputs/OP_Scraper/articles_with_scraped_content.csv`
- **Format:** Easy-to-read spreadsheet
- **Columns:**
  - `#` - Article number
  - `Title` - Article title (100 chars)
  - `Source` - News source (BBC, Bloomberg, Reuters, etc.)
  - `Published Date` - Publication timestamp
  - **Scraped Content Length** - How many characters were scraped
  - `Summary` - First 200 chars of AI summary
  - `Event Class` - Main category (Geo_Political, Financial_Market, etc.)
  - `Direction` - Sentiment (positive/negative/neutral)

---

### 3. **scraped_content_summary.json** (Compact JSON)
- **Location:** `Outputs/OP_Scraper/scraped_content_summary.json`
- **Format:** JSON with all selected articles
- **Fields for each article:**
  ```json
  {
    "title": "...",
    "source": "...",
    "link": "...",
    "published_date": "...",
    "scraped_content": "FULL SCRAPED TEXT HERE",
    "summary": "AI summary",
    "event_class": "...",
    "direction": "..."
  }
  ```

---

### 4. **Individual Markdown Files** (Detailed Readables)
- **Location:** `Outputs/OP_Scraper/articles_detailed/`
- **Format:** One markdown file per article
- **Naming:** `001_Article_Title.md`, `002_Next_Article.md`, etc.
- **Content:**
  ```markdown
  # Article Title
  
  **Source:** BBC World | **Date:** 2026-05-29
  **Link:** https://...
  
  ## 📰 Scraped Content
  [FULL ARTICLE TEXT HERE - thousands of characters]
  
  ## 📋 AI-Generated Summary
  [4-5 sentence comprehensive summary]
  
  ## 🏷️ Classification & Insights
  - Event Class: Geo_Political
  - Sub-Type: Geopolitical_Events
  - Channel: Armed Conflict
  - Sentiment: negative (Score: -3)
  - Trade Impact: EST:~10% of India's defense imports
  - Origin: Israel / Lebanon
  
  ## ✅ Processing Steps
  - ✓ Word-to-word Cleaning (PASSED)
  - ✓ Relevance Check (PASSED)
  - ✓ Scraping (PASSED: Successfully scraped 8234 characters)
  - ✓ Semantic Deduplication (PASSED)
  - ✓ Multimedia Filter (PASSED)
  - ✓ Generate Summary (PASSED)
  - ✓ Taxonomy Classification (PASSED)
  - ✓ Direction Analysis (PASSED)
  - ✓ Trade Share Analysis (PASSED)
  - ✓ Geographic Origin (PASSED)
  - ✓ Save to Database (PASSED)
  ```

---

## 🔍 How to Access the Scraped Content

### **EASIEST (Fastest)**
👉 Open `Outputs/OP_Scraper/articles_detailed/` folder and view the `.md` files

### **For Data Analysis**
👉 Open `Outputs/OP_Scraper/articles_with_scraped_content.csv` in Excel

### **For Programmatic Access**
👉 Load `Outputs/OP_Scraper/scraped_content_summary.json` or `newsfeeds_scrape_log.json`

### **Original Full Log**
👉 `newsfeeds_scrape_log.json` has everything with `selected_articles[].scraped_content`

---

## 📊 Summary of Content

Each article contains:

| Field | Description | Example Length |
|-------|-------------|-----------------|
| **Title** | Headline | ~100 chars |
| **Scraped Content** | Full article text | 2,000-15,000 chars |
| **Summary** | AI-generated (4-5 sentences) | ~500-800 chars |
| **Classification** | Event class, Sub-type, Channel | Structured |
| **Sentiment** | Direction & impact score | -5 to +5 |
| **Trade Impact** | India-specific impact estimate | ~100 chars |
| **Origin** | Geographic source of news | ~50 chars |

---

## ⏱️ Processing Status

- **Fetching & Deduplication** → Usually 1-2 minutes
- **Relevance Filtering** → 1-2 minutes (LLM calls)
- **Content Scraping** → 2-3 minutes (4-tier scraper)
- **LLM Analysis** (Summary, Classification, Direction, etc.) → 3-5 minutes
- **Database & File Writing** → 30 seconds

**Total:** ~8-15 minutes for full pipeline

---

## ✅ Verification Checklist

After running the scraper, verify:

- [ ] `newsfeeds_scrape_log.json` exists and has `selected_articles` section
- [ ] `Outputs/OP_Scraper/articles_with_scraped_content.csv` has multiple rows
- [ ] `Outputs/OP_Scraper/articles_detailed/` folder has `.md` files
- [ ] Each `.md` file contains full scraped article text
- [ ] Database updated with 550+ articles

---

## 💡 Tips

- **To view all scraped content quickly:** Use Excel/Google Sheets to open the CSV file
- **To search content:** Use VS Code's search across the `articles_detailed/` folder
- **To export for other tools:** Use the JSON files and parse with Python/Node
- **To share with others:** Send the markdown files or CSV

---

Last Updated: May 29, 2026
