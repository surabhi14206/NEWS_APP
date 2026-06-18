import zipfile
import xml.etree.ElementTree as ET

def extract_all(docx_path):
    namespaces = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    }
    
    with zipfile.ZipFile(docx_path) as docx:
        xml_content = docx.read('word/document.xml')
        root = ET.fromstring(xml_content)
        
        # We can extract text paragraph by paragraph and see the tables in relation to text
        body = root.find('.//w:body', namespaces)
        if body is None:
            print("No body found")
            return
            
        child_count = 0
        for child in body:
            tag = child.tag.split('}')[-1]
            if tag == 'p':
                # Paragraph
                text = "".join(node.text for node in child.findall('.//w:t', namespaces) if node.text)
                if text.strip():
                    print(f"[P] {text.strip()}")
            elif tag == 'tbl':
                # Table
                rows = []
                for row in child.findall('.//w:tr', namespaces):
                    cells = []
                    for cell in row.findall('.//w:tc', namespaces):
                        cell_text = "".join(node.text for node in cell.findall('.//w:t', namespaces) if node.text)
                        cells.append(cell_text.strip())
                    rows.append(cells)
                print(f"[TBL] Found table with {len(rows)} rows:")
                for r_idx, r in enumerate(rows):
                    print(f"  Row {r_idx}: {r}")

docx_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\Indian_Economy_News_Report_Filtered_15Jun2026.docx"
extract_all(docx_path)
