import os
import docx
from docx.text.paragraph import Paragraph
from docx.table import Table


def _extract_links_from_paragraph(paragraph, doc) -> list:
    """
    Extracts hyperlinks and their target URLs from a DOCX paragraph element.
    """
    links = []
    for child in paragraph._p:
        if child.tag.endswith('hyperlink'):
            r_id = child.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            link_text = "".join(child.itertext()).strip()
            if r_id and r_id in doc.part.rels:
                target_url = doc.part.rels[r_id].target_ref
                links.append({"text": link_text, "url": target_url})
    return links


def parse_docx(file_path: str) -> dict:
    """
    Parses a DOCX document into a clean, order-preserving dictionary representation.
    Extracts paragraphs, tables, and hyperlinks in their exact document sequence
    without interpretation or LLM calls.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = docx.Document(file_path)
    elements = []

    for child in doc.element.body:
        if child.tag.endswith('p'):
            p = Paragraph(child, doc)
            text = p.text.strip()
            if text:
                item = {
                    "type": "paragraph",
                    "text": text,
                    "style": p.style.name if p.style else "Normal"
                }
                links = _extract_links_from_paragraph(p, doc)
                if links:
                    item["links"] = links
                elements.append(item)
        elif child.tag.endswith('tbl'):
            table = Table(child, doc)
            table_rows = []
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells]
                table_rows.append(row_cells)
            if table_rows:
                elements.append({
                    "type": "table",
                    "rows": table_rows
                })

    return {
        "file_name": os.path.basename(file_path),
        "total_elements": len(elements),
        "elements": elements
    }
