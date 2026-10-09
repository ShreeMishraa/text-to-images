import os
import re
import docx
from docx.text.paragraph import Paragraph
from docx.table import Table

try:
    import pypdf
except ImportError:
    pypdf = None


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


def _infer_shot_type(visual_text: str, scene: str) -> str:
    """Determines shot type based on script formatting cues."""
    text_upper = visual_text.upper()
    if "SPLIT SCREEN" in text_upper:
        return "Split Screen"
    elif "FSA" in text_upper or "FULL SCREEN" in text_upper:
        return "FSA"
    elif "MOG" in text_upper or "MOTION GRAPHIC" in text_upper:
        return "MOG"
    elif "TITLE CARD" in text_upper or "SUMMARY CARD" in text_upper:
        return "Title Card"
    elif "STUDIO" in scene.upper() or "PRESENTER" in text_upper:
        return "Mid Shot"
    return "FSA"


def parse_script_to_panels(file_path: str) -> dict:
    """
    Parses a client script (.docx or .pdf) and outputs a structured panel sequence.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    raw_elements = []
    metadata = {}

    if ext == ".docx":
        doc = docx.Document(file_path)
        for child in doc.element.body:
            if child.tag.endswith('p'):
                p = Paragraph(child, doc)
                text = p.text.strip()
                if text:
                    links = _extract_links_from_docx_paragraph(p, doc)
                    raw_elements.append({"type": "paragraph", "text": text, "links": links})
            elif child.tag.endswith('tbl'):
                table = Table(child, doc)
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if len(cells) >= 2 and cells[0]:
                        metadata[cells[0]] = cells[1]

    elif ext == ".pdf":
        if pypdf is None:
            raise ImportError("pypdf is required for PDF parsing")
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                for line in text.split('\n'):
                    line_str = line.strip()
                    if line_str:
                        raw_elements.append({"type": "paragraph", "text": line_str, "links": []})

    # Segment into structured panels
    panels = []
    current_scene = "NA"
    current_panel = None
    current_speaker = None
    current_audio_mode = "SYNC"

    def finalize_panel():
        nonlocal current_panel
        if current_panel and (current_panel["visual_instructions"] or current_panel["dialogue"] or current_panel["text_overlays"]):
            panels.append(current_panel)
            current_panel = None

    def start_new_panel(shot_type="FSA"):
        finalize_panel()
        nonlocal current_panel
        current_panel = {
            "panel_id": len(panels) + 1,
            "shot_type": shot_type,
            "scene": current_scene,
            "visual_instructions": [],
            "dialogue": None,
            "speaker": current_speaker or "NA",
            "audio_mode": current_audio_mode,
            "text_overlays": [],
            "references": [],
            "links": []
        }

    start_new_panel("Mid Shot")

    for elem in raw_elements:
        text = elem["text"]
        links = elem.get("links", [])

        # Scene Cuts
        if text.startswith("CUT TO:") or text.startswith("INT.") or text.startswith("EXT."):
            if "STUDIO" in text:
                current_scene = text.replace("CUT TO:", "").strip()
            else:
                current_scene = text
            start_new_panel("Mid Shot")

        # Visual Cue Section
        elif any(cue in text for cue in ["FSA:", "INSERT MoG:", "INSERT TWO-WAY SPLIT SCREEN:", "INSERT THREE-WAY SPLIT SCREEN:", "INSERT TITLE CARD:"]):
            shot = _infer_shot_type(text, current_scene)
            start_new_panel(shot)
            current_panel["visual_instructions"].append(text)

        # TOS / On-Screen Text
        elif text.startswith("TOS:") or text.startswith("TOS (on cue):") or text.startswith("TOS10"):
            tos_text = re.sub(r"^TOS.*?:", "", text).strip()
            if current_panel is None:
                start_new_panel("FSA")
            current_panel["text_overlays"].append(tos_text)

        # Dialogue Speakers
        elif text in ["PRESENTER", "PRESENTER (V.O.)"]:
            current_speaker = "Presenter"
            current_audio_mode = "V.O." if "(V.O.)" in text else "SYNC"

        # Dialogue / Beats
        elif current_speaker and not text.startswith("(") and not text.endswith(")"):
            if current_panel is None:
                start_new_panel("Mid Shot" if current_audio_mode == "SYNC" else "FSA")
            current_panel["speaker"] = current_speaker
            current_audio_mode_mode = current_audio_mode
            current_panel["audio_mode"] = current_audio_mode
            if current_panel["dialogue"]:
                # Create next panel beat for subsequent dialogue line
                start_new_panel(current_panel["shot_type"])
                current_panel["speaker"] = current_speaker
                current_panel["audio_mode"] = current_audio_mode
            current_panel["dialogue"] = text

        # Visual description lines / references
        else:
            if current_panel is None:
                start_new_panel("FSA")
            current_panel["visual_instructions"].append(text)

            # Capture visual reference tags (e.g., ref 1, ref 2)
            refs = re.findall(r'\(ref\s*\d+.*?\)', text, re.IGNORECASE)
            if refs:
                current_panel["references"].extend(refs)

        # Attach links if present
        if links and current_panel:
            current_panel["links"].extend(links)

    finalize_panel()

    return {
        "file_name": os.path.basename(file_path),
        "metadata": metadata,
        "total_panels": len(panels),
        "panels": panels
    }