"""
Brick 1: Document Parser.
Parses script (.docx or .pdf) and extracts visual reference images 
from reference files (.pdf or .docx).
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


def _extract_links_from_docx_paragraph(paragraph, doc) -> list:
    links = []
    for child in paragraph._p:
        if child.tag.endswith('hyperlink'):
            r_id = child.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            link_text = "".join(child.itertext()).strip()
            if r_id and r_id in doc.part.rels:
                links.append({"text": link_text, "url": doc.part.rels[r_id].target_ref})
    return links


def parse_docx(file_path: str) -> dict:
    """Parses text, metadata, and links from a .docx file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    doc = docx.Document(file_path)
    elements = []
    metadata = {}

    for child in doc.element.body:
        if child.tag.endswith('p'):
            p = Paragraph(child, doc)
            text = p.text.strip()
            if text:
                item = {"type": "paragraph", "text": text, "style": p.style.name if p.style else "Normal"}
                links = _extract_links_from_docx_paragraph(p, doc)
                if links:
                    item["links"] = links
                elements.append(item)
        elif child.tag.endswith('tbl'):
            table = Table(child, doc)
            table_rows = []
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells]
                if len(row_cells) >= 2 and row_cells[0]:
                    metadata[row_cells[0]] = row_cells[1]
                table_rows.append(row_cells)
            if table_rows:
                elements.append({"type": "table", "rows": table_rows})

    return {
        "file_name": os.path.basename(file_path),
        "format": "docx",
        "metadata": metadata,
        "total_elements": len(elements),
        "elements": elements
    }


def parse_pdf(file_path: str) -> dict:
    """Parses text blocks and metadata from a .pdf file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    if pypdf is None:
        raise ImportError("pypdf is required for parsing PDF files")

    reader = pypdf.PdfReader(file_path)
    elements = []
    metadata = {}

    for page in reader.pages:
        text = page.extract_text()
        if text:
            for line in text.split('\n'):
                line_str = line.strip()
                if line_str:
                    elements.append({"type": "paragraph", "text": line_str, "links": []})

    return {
        "file_name": os.path.basename(file_path),
        "format": "pdf",
        "metadata": metadata,
        "total_elements": len(elements),
        "elements": elements
    }


def extract_reference_images_from_pdf(pdf_path: str, output_dir: str = "output/refs") -> dict:
    """Extracts embedded images from a reference PDF file."""
    if not pdf_path or not os.path.exists(pdf_path) or pypdf is None:
        return {}

    os.makedirs(output_dir, exist_ok=True)
    reader = pypdf.PdfReader(pdf_path)
    ref_image_map = {}
    img_counter = 1

    for page in reader.pages:
        for img in page.images:
            img_filename = f"ref_{img_counter:03d}.png"
            img_path = os.path.join(output_dir, img_filename)
            try:
                with open(img_path, "wb") as f:
                    f.write(img.data)
                ref_key = f"ref {img_counter}"
                ref_image_map[ref_key] = img_path
                img_counter += 1
            except Exception as e:
                print(f"[Warning] Could not save PDF reference image {img_counter}: {e}")

    return ref_image_map


def extract_reference_images_from_docx(docx_path: str, output_dir: str = "output/refs") -> dict:
    """Extracts embedded images from a reference DOCX file archive."""
    if not docx_path or not os.path.exists(docx_path):
        return {}

    os.makedirs(output_dir, exist_ok=True)
    ref_image_map = {}
    img_counter = 1

    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            for filename in z.namelist():
                if filename.startswith('word/media/'):
                    ext = os.path.splitext(filename)[1]
                    img_filename = f"ref_{img_counter:03d}{ext}"
                    img_path = os.path.join(output_dir, img_filename)
                    with open(img_path, 'wb') as f:
                        f.write(z.read(filename))
                    ref_key = f"ref {img_counter}"
                    ref_image_map[ref_key] = img_path
                    img_counter += 1
    except Exception as e:
        print(f"[Warning] Could not extract images from DOCX reference: {e}")

    return ref_image_map


def extract_reference_images(ref_path: str, output_dir: str = "output/refs") -> dict:
    """Dispatches reference image extraction based on file extension (.pdf or .docx)."""
    if not ref_path or not os.path.exists(ref_path):
        return {}
    ext = os.path.splitext(ref_path)[1].lower()
    if ext == ".pdf":
        return extract_reference_images_from_pdf(ref_path, output_dir)
    elif ext in [".docx", ".doc"]:
        return extract_reference_images_from_docx(ref_path, output_dir)
    return {}


def parse_script(file_path: str) -> dict:
    """Unified entry point for raw file extraction (DOCX or PDF)."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".docx", ".doc"]:
        return parse_docx(file_path)
    elif ext == ".pdf":
        return parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported format: {ext}")


def parse_script_to_panels(script_path: str, ref_path: str = None) -> dict:
    """
    Parses ANY script (.docx or .pdf) and attaches images from ANY reference file (.pdf or .docx).
    """
    raw_doc = parse_script(script_path)
    elements = raw_doc.get("elements", [])
    metadata = raw_doc.get("metadata", {})

    # Extract reference images from reference file
    ref_images_map = extract_reference_images(ref_path) if ref_path else {}

    panels = []
    current_scene = "NA"
    current_shot = "Mid Shot"
    current_speaker = None
    current_audio_mode = "SYNC"

    i = 0
    while i < len(elements):
        el = elements[i]
        if el["type"] != "paragraph":
            i += 1
            continue

        text = el["text"]
        links = el.get("links", [])

        # Scene Transitions
        if text.startswith("CUT TO:") or text.startswith("INT.") or text.startswith("EXT."):
            current_scene = text.replace("CUT TO:", "").strip() if "STUDIO" in text else text
            i += 1
            continue

        # Shot Cues
        if any(text.startswith(cue) for cue in ["FADE IN:", "FSA:", "INSERT MoG:", "INSERT TWO-WAY SPLIT SCREEN:", "INSERT THREE-WAY SPLIT SCREEN:", "INSERT TITLE CARD:"]):
            if "SPLIT SCREEN" in text:
                current_shot = "Split Screen"
            elif "MoG" in text:
                current_shot = "MOG"
            elif "TITLE CARD" in text:
                current_shot = "Title Card"
            else:
                current_shot = "FSA"
            i += 1
            continue

        # Structural Markers
        if text in ["MoG Ends.", "SPLIT SCREEN ENDS.", "FADE OUT.", "(beat)"]:
            i += 1
            continue

        # Presenter State
        if text in ["PRESENTER", "PRESENTER (V.O.)"]:
            current_speaker = "Presenter"
            current_audio_mode = "V.O." if "(V.O.)" in text else "SYNC"
            i += 1
            continue

        # TOS Badges
        if text.startswith("TOS:") or text.startswith("TOS (on cue):") or text.startswith("TOS10"):
            tos_val = re.sub(r"^TOS.*?:", "", text).strip()
            if panels:
                panels[-1]["text_overlays"].append({
                    "badge_type": "tos_yellow_pill",
                    "text": tos_val,
                    "position": "bottom_center"
                })
            i += 1
            continue

        # Extract ref tags e.g. (ref 1)
        refs = re.findall(r'\(ref\s*\d+.*?\)', text, re.IGNORECASE)
        ref_image_paths = []
        for r in refs:
            clean_ref_key = r.strip("()").lower()
            if clean_ref_key in ref_images_map:
                ref_image_paths.append(ref_images_map[clean_ref_key])

        is_dialogue = current_speaker and not any(text.startswith(p) for p in [
            "Show ", "Left screen:", "Right screen:", "Centre screen:", "Freeze ", "Highlight ", "Animate ", "Transition "
        ])

        is_present = (current_speaker == "Presenter" and current_audio_mode == "SYNC")
        layout_mode = "full_bleed"
        if "SPLIT SCREEN" in text.upper():
            layout_mode = "split_2way" if "TWO-WAY" in text.upper() else "split_3way"

        panel = {
            "panel_id": len(panels) + 1,
            "shot_type": current_shot,
            "scene": current_scene,
            "presenter": {
                "is_present": is_present,
                "audio_mode": current_audio_mode if is_dialogue else "NA",
                "position": "center" if is_present else "NA",
                "dialogue": text if is_dialogue else "NA"
            },
            "canvas_layout": {
                "layout_mode": layout_mode,
                "primary_subject": text[:80],
                "visual_description": text if not is_dialogue else "Presenter speaking in studio.",
                "visual_state_delta": f"Beat {len(panels) + 1}"
            },
            "vector_annotations": [],
            "text_overlays": [],
            "references": refs,
            "ref_image_paths": ref_image_paths,
            "links": links
        }

        panels.append(panel)
        i += 1

    return {
        "title": metadata.get("Title", "Untitled Storyboard"),
        "script_code": metadata.get("Script Code"),
        "total_panels": len(panels),
        "panels": panels
    }