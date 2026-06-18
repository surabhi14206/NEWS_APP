import docx
import re

original_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\docs_7_Days.docx"
doc = docx.Document(original_path)

keep_criteria = [
    r"\bIndia\b", r"\bIndian\b", r"\bRupee\b", r"\bRBI\b", r"\bNifty\b", r"\bModi\b", r"\bMacron\b",
    r"\bJaishankar\b", r"\bTata\b", r"\bAirbus\b", r"\bOman\b", r"\bTCS\b", r"\bRazorpay\b", r"\bethanol\b",
    r"\bhydropower\b", r"\bmonsoon\b", r"\bEl Niño\b", r"\bfertilizer\b"
]

remove_criteria = [
    r"\bECB\b", r"\bFed\b", r"\bBOE\b", r"\bTurkey\b", r"\bTurkish\b", r"\bNew Zealand\b", r"\bBrazil\b",
    r"\bPix\b", r"\bSouth Africa\b", r"\bGreek\b", r"\bLNG\b", r"\bIndonesia\b", r"\bFrench wine\b", r"\bAmazon\b"
]

kept = []
removed = []

for idx, row in enumerate(doc.tables[0].rows[1:]):
    date_src = row.cells[0].text.strip()
    title = row.cells[1].text.strip()
    sector = row.cells[2].text.strip()
    direction = row.cells[3].text.strip()
    
    # Check if we should keep or remove
    has_keep = any(re.search(pat, title, re.IGNORECASE) or re.search(pat, sector, re.IGNORECASE) for pat in keep_criteria)
    has_remove = any(re.search(pat, title, re.IGNORECASE) for pat in remove_criteria)
    
    # Specific removals
    is_accident = "road accident" in title.lower() or "fire inspection" in title.lower() or "nicobar" in title.lower()
    
    if (has_keep and not has_remove and not is_accident) or "Razorpay" in title or "Oman" in title:
        kept.append((title, sector, direction))
    else:
        removed.append((title, sector, direction))

print(f"Kept count: {len(kept)}")
print(f"Removed count: {len(removed)}")

print("\nSAMPLE KEPT:")
for t, s, d in kept[:10]:
    print(f"- {t} ({s})")

print("\nSAMPLE REMOVED:")
for t, s, d in removed[:10]:
    print(f"- {t} ({s})")
