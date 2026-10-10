"""
Brick 1: Universal Script Document Parser & Reference Image Extractor.
Extracts script beats, metadata, tables, and embedded reference images from ANY uploaded .docx/.pdf.
"""

import os
import re
import zipfile
import docx
from docx.text.paragraph import Paragraph
from docx.table import Table

try:
    import pypdf
except ImportError:
    pypdf = None


def clean_parsed_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_docx(file_path: str) -> dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = docx.Document(file_path)
    elements = []
    metadata = {}

    for child in doc.element.body:
        if child.tag.endswith('p'):
            p = Paragraph(child, doc)
            text = clean_parsed_text(p.text)
            if text:
                elements.append({"type": "paragraph", "text": text})
        elif child.tag.endswith('tbl'):
            table = Table(child, doc)
            for row in table.rows:
                row_cells = [clean_parsed_text(cell.text) for cell in row.cells]
                if len(row_cells) >= 2 and row_cells[0]:
                    metadata[row_cells[0]] = row_cells[1]

    return {
        "file_name": os.path.basename(file_path),
        "metadata": metadata,
        "elements": elements
    }


def parse_pdf(file_path: str) -> dict:
    if not os.path.exists(file_path) or pypdf is None:
        return {"elements": [], "metadata": {}}

    reader = pypdf.PdfReader(file_path)
    elements = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            for line in text.split('\n'):
                line_str = clean_parsed_text(line)
                if line_str:
                    elements.append({"type": "paragraph", "text": line_str})

    return {"file_name": os.path.basename(file_path), "metadata": {}, "elements": elements}


def extract_reference_images(ref_path: str, output_dir: str = "output/refs") -> dict:
    if not ref_path or not os.path.exists(ref_path):
        return {}
    os.makedirs(output_dir, exist_ok=True)
    ref_image_map = {}
    img_counter = 1

    ext = os.path.splitext(ref_path)[1].lower()
    if ext == ".pdf" and pypdf:
        reader = pypdf.PdfReader(ref_path)
        for page in reader.pages:
            for img in page.images:
                img_path = os.path.join(output_dir, f"ref_{img_counter:03d}.png")
                with open(img_path, "wb") as f:
                    f.write(img.data)
                ref_image_map[f"ref {img_counter}"] = img_path
                img_counter += 1
    elif ext in [".docx", ".doc"]:
        try:
            with zipfile.ZipFile(ref_path, 'r') as z:
                for filename in z.namelist():
                    if filename.startswith('word/media/'):
                        ext_img = os.path.splitext(filename)[1]
                        img_path = os.path.join(output_dir, f"ref_{img_counter:03d}{ext_img}")
                        with open(img_path, 'wb') as f:
                            f.write(z.read(filename))
                        ref_image_map[f"ref {img_counter}"] = img_path
                        img_counter += 1
        except Exception:
            pass

    return ref_image_map


def parse_script_to_panels(script_path: str, ref_path: str = None) -> dict:
    ext = os.path.splitext(script_path)[1].lower()
    raw_doc = parse_docx(script_path) if ext in [".docx", ".doc"] else parse_pdf(script_path)
    elements = raw_doc.get("elements", [])
    metadata = raw_doc.get("metadata", {})
    ref_images_map = extract_reference_images(ref_path) if ref_path else {}

    parsed_paragraphs = []
    for el in elements:
        text = el["text"].strip()
        if not text or "For Internal Use Only" in text:
            continue
        parsed_paragraphs.append(text)

    return {
        "title": metadata.get("Title", "Educational Storyboard Script"),
        "script_code": metadata.get("Script Code", "GENERIC_01"),
        "raw_paragraphs": parsed_paragraphs,
        "ref_images_map": ref_images_map
    }