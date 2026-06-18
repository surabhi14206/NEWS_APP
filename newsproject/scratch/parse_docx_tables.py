import zipfile
import xml.etree.ElementTree as ET

def extract_tables(docx_path):
    namespaces = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
    }
    
    with zipfile.ZipFile(docx_path) as docx:
        xml_content = docx.read('word/document.xml')
        root = ET.fromstring(xml_content)
        
        tables = []
        for table in root.findall('.//w:tbl', namespaces):
            rows = []
            for row in table.findall('.//w:tr', namespaces):
                cells = []
                for cell in row.findall('.//w:tc', namespaces):
                    # Combine all text within this cell
                    cell_text = "".join(node.text for node in cell.findall('.//w:t', namespaces) if node.text)
                    cells.append(cell_text.strip())
                rows.append(cells)
            tables.append(rows)
        return tables

docx_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\Indian_Economy_News_Report_Filtered_15Jun2026.docx"
tables = extract_tables(docx_path)
print(f"Found {len(tables)} tables")

for idx, table in enumerate(tables):
    print(f"\nTable {idx+1} has {len(table)} rows:")
    if table:
        print("Header/First row:", table[0])
        print("Row 2:", table[1] if len(table) > 1 else "N/A")
        print("Row 3:", table[2] if len(table) > 2 else "N/A")
        print("Last row:", table[-1])
