import os
import docx
from docx.text.paragraph import Paragraph
from docx.table import Table

try:
    import pymupdf
except ImportError:
    pymupdf = None


def _extract_links_from_docx_paragraph(paragraph, doc) -> list:
    """Extracts hyperlinks and their target URLs from a DOCX paragraph."""
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
    Parses a DOCX document in exact document order with tables and links.
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
                links = _extract_links_from_docx_paragraph(p, doc)
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
        "format": "docx",
        "total_elements": len(elements),
        "elements": elements
    }


def parse_pdf(file_path: str) -> dict:
    """
    Parses a PDF script in exact order, extracting tables, text blocks, and links.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if pymupdf is None:
        raise ImportError("pymupdf is required for parsing PDF files")

    doc = pymupdf.open(file_path)
    elements = []

    for page in doc:
        # 1. Extract tables
        tables = list(page.find_tables())
        table_bboxes = [t.bbox for t in tables]
        for t in tables:
            extracted = t.extract()
            clean_rows = [[(cell.strip() if cell else '') for cell in r] for r in extracted]
            if any(any(c for c in r) for r in clean_rows):
                elements.append({
                    "type": "table",
                    "rows": clean_rows
                })

        # 2. Extract page hyperlinks
        page_links = []
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                rect = link.get("from")
                link_text = page.get_text("text", clip=rect).strip() if rect else ""
                page_links.append({
                    "text": link_text or "Link",
                    "url": uri,
                    "rect": list(rect) if rect else None
                })

        # 3. Extract text blocks (excluding areas inside tables)
        blocks = page.get_text("blocks")
        for b in blocks:
            text = b[4].strip()
            if not text:
                continue
            bbox = b[:4]
            inside_table = any(
                bbox[0] >= tb[0] - 2 and bbox[1] >= tb[1] - 2 and bbox[2] <= tb[2] + 2 and bbox[3] <= tb[3] + 2
                for tb in table_bboxes
            )
            if not inside_table:
                # Associate links whose coordinates fall within this block
                block_links = []
                for pl in page_links:
                    if pl.get("rect"):
                        lr = pl["rect"]
                        if not (lr[3] < bbox[1] or lr[1] > bbox[3]):
                            block_links.append({"text": pl["text"], "url": pl["url"]})

                item = {
                    "type": "paragraph",
                    "text": text,
                    "style": "Normal"
                }
                if block_links:
                    item["links"] = block_links
                elements.append(item)

    return {
        "file_name": os.path.basename(file_path),
        "format": "pdf",
        "total_elements": len(elements),
        "elements": elements
    }


def parse_script(file_path: str) -> dict:
    """
    Unified entry point for ingesting client scripts in DOCX or PDF format.
    Automatically detects format and dispatches to the deterministic parser.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".pdf":
        return parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Expected .docx or .pdf")
