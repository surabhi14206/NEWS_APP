import sys
import os
import zipfile
import xml.etree.ElementTree as ET

def read_docx_text(file_path) -> str:
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            texts = [node.text for node in root.findall('.//w:t', namespaces) if node.text]
            return "\n".join(texts)
    except Exception as e:
        return f"Error: {e}"

docx_path = r"c:\Users\yadav\OneDrive\Desktop\Python\NEWS_APP\Docs_DB\Indian_Economy_News_Report_Filtered_15Jun2026.docx"
text = read_docx_text(docx_path)
print("TOTAL LENGTH:", len(text))
print("FIRST 2000 CHARACTERS:")
print(text[:2000])
print("\nLAST 2000 CHARACTERS:")
print(text[-2000:])
