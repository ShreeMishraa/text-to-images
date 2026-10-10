"""
Brick 3: Master Prompt Builder & PDF Exporter.
Constructs highly detailed educational storyboard prompts that match client reference specs.
Supports flexible style detection (color studio/graphic overlays vs. monochrome artwork)
and detailed per-panel asset compositions.
"""

import os
import re
import json
from fpdf import FPDF


def sanitize_text(text: str) -> str:
    if not text:
        return "NA"
    replacements = {
        '•': '-', '–': '-', '—': '-', '“': '"', '”': '"',
        '‘': "'", '’': "'", '…': '...'
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode('latin-1', 'replace').decode('latin-1')


def clean_text_descriptors(text: str) -> str:
    if not text:
        return ""
    # Clean OCR duplicate words (e.g., 'clear clear', 'ripe-lush')
    text = re.sub(r"\b(clear|lush|ripe|green)\s+\1\b", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_image_prompt(panel_spec: dict, global_style_override: str = None) -> str:
    """
    Builds an expansive, high-detail prompt tailored for educational storyboards.
    Dynamically checks if monochrome line-art is explicitly requested; 
    otherwise default to clean, realistic/vector educational graphics & live presenter studio.
    """
    layout = panel_spec.get("canvas_layout", {})
    vis_desc = clean_text_descriptors(layout.get("visual_description", ""))
    shot_type = panel_spec.get("shot_type", "Mid Shot")
    layout_mode = layout.get("layout_mode", "full_bleed")
    scene_str = (panel_spec.get("scene") or "").upper()
    
    # 1. Determine Visual Aesthetic (Color vs. Grayscale)
    # Default to clean educational color visual unless explicitly instructed by ref doc / prompt
    is_explicit_monochrome = False
    combined_check_text = (vis_desc + " " + (global_style_override or "")).lower()
    
    if any(k in combined_check_text for k in ["monochrome", "grayscale", "black and white", "line art", "pencil sketch"]):
        is_explicit_monochrome = True

    if is_explicit_monochrome:
        style_anchor = (
            "Aesthetic Style: Fine black and white line-art pencil and ink illustration, crisp graphite linework, "
            "detailed hatching, high contrast, clean white background, 16:9 widescreen layout."
        )
    else:
        style_anchor = (
            "Aesthetic Style: Professional 16:9 widescreen educational broadcast video layout, high quality, "
            "clean lighting, vibrant crisp graphics, clean studio background."
        )

    # 2. Composition & Layout Specifications
    comp_parts = []
    if layout_mode == "split_3way" or "3-way" in vis_desc.lower() or "three-way" in vis_desc.lower():
        comp_parts.append(
            "Composition: Clean 3-way vertical split screen layout divided into three equal side-by-side panels "
            "separated by thin neat black border lines."
        )
    elif layout_mode == "split_2way" or "split" in vis_desc.lower():
        comp_parts.append(
            "Composition: Clean 2-way vertical split screen layout divided into two equal side-by-side panels "
            "separated by a neat dividing line."
        )
    elif layout_mode == "presenter_with_mog_inset" or "MOG" in shot_type:
        comp_parts.append(
            "Composition: MOG Layout. Left side features the presenter standing in an educational studio facing the camera. "
            "Right side features a distinct clean graphic card floating in the frame with high contrast details."
        )
    elif shot_type == "Mid Shot":
        comp_parts.append("Composition: Mid shot framing centered on presenter speaking directly to camera in an educational video studio.")
    elif shot_type in ["FSA", "Full Screen Graphic", "Title card", "TOS 1"]:
        comp_parts.append(f"Composition: Full screen graphic layout ({shot_type}) formatted for clarity and educational presentation.")
    else:
        comp_parts.append(f"Composition: {shot_type} framing with clear visual focal points.")

    # 3. Subject, Details, and Contextual Scene Building
    detail_parts = []
    
    # Context-aware asset enhancement
    if "classroom" in vis_desc.lower() or "INT. CLASSROOM" in scene_str:
        detail_parts.append(
            "Setting: Indian middle-school science laboratory. Environment includes a neat blackboard in background with clean text, "
            "wooden science bench, terracotta clay pots with printed labels ('DARK SOIL', 'RED SOIL', 'SANDY SOIL'), and students in uniform."
        )
    elif "studio" in vis_desc.lower() or "INT. STUDIO" in scene_str:
        detail_parts.append(
            "Setting: Modern minimalist educational broadcast studio with soft neutral studio backdrop and clean studio floor."
        )
    elif any(k in vis_desc.lower() for k in ["map", "uk", "india", "canada", "sweden", "usa"]):
        detail_parts.append(
            "Graphic Asset: Highly detailed, crisp geographic map graphic with vibrant regional highlighting and bold outline labels."
        )

    detail_parts.append(f"Primary Action & Scene Details: {vis_desc}")

    # 4. Text Overlay Directives
    text_directives = []
    tos_items = panel_spec.get("text_overlays", [])
    if tos_items:
        tos_str = " | ".join([clean_text_descriptors(t['text'] if isinstance(t, dict) else t) for t in tos_items])
        text_directives.append(
            f"On-Screen Text Elements: Render clean graphic text box badge displaying EXACT text: \"{tos_str}\". "
            "Typography must be bold, legible, and centered within the graphic badge."
        )
    else:
        text_directives.append("On-Screen Text Elements: No text overlays outside specified visual graphic elements.")

    # 5. Negative Prompt & Quality Constraints
    constraints = [
        "Constraints: High educational visual clarity, balanced framing, no watermarks, no logos, "
        "no camera equipment or tripods visible inside the frame, no extra random text."
    ]

    # Combine into a rich, detailed master prompt
    full_prompt_sections = [
        style_anchor,
        " ".join(comp_parts),
        " ".join(detail_parts),
        " ".join(text_directives),
        " ".join(constraints)
    ]

    return "\n".join([s for s in full_prompt_sections if s]).strip()


class StoryboardPromptPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(self.epw, 10, 'Master Storyboard Panel Prompts', border=0, new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_font('Helvetica', 'I', 10)
        self.cell(self.epw, 5, 'Client Approved 16:9 Visual Specifications', border=0, new_x="LMARGIN", new_y="NEXT", align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(self.epw, 10, f'Page {self.page_no()}', border=0, new_x="LMARGIN", new_y="NEXT", align='C')


def generate_prompts_pdf(plan_data: dict, output_pdf_path: str = "output/all_storyboard_prompts.pdf") -> str:
    pdf = StoryboardPromptPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    title = sanitize_text(plan_data.get("title", "Storyboard Script"))
    panels = plan_data.get("panels", [])

    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(pdf.epw, 8, f"Document: {title}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(pdf.epw, 8, f"Total Panels: {len(panels)}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    for panel in panels:
        pid = panel.get("panel_id")
        shot_type = sanitize_text(panel.get("shot_type", "FSA"))
        scene = sanitize_text(panel.get("scene", "NA"))

        presenter = panel.get("presenter", {})
        dialogue = sanitize_text(presenter.get("dialogue", "NA"))
        audio_mode = sanitize_text(presenter.get("audio_mode", "SYNC"))

        layout = panel.get("canvas_layout", {})
        visual_desc = sanitize_text(layout.get("visual_description", ""))

        prompt = sanitize_text(build_image_prompt(panel))

        # Panel Section Header
        pdf.set_x(pdf.l_margin)
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(pdf.epw, 8, f" PANEL {pid:03d} | Shot: {shot_type} | Scene: {scene}", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font('Helvetica', '', 10)
        if dialogue != "NA":
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5, f"Dialogue ({audio_mode}): {dialogue}", new_x="LMARGIN", new_y="NEXT")
        if visual_desc:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(pdf.epw, 5, f"Visual Notes: {visual_desc}", new_x="LMARGIN", new_y="NEXT")

        tos_items = panel.get("text_overlays", [])
        if tos_items:
            tos_str = " | ".join([sanitize_text(t['text'] if isinstance(t, dict) else t) for t in tos_items])
            pdf.set_font('Helvetica', 'B', 9)
            pdf.set_x(pdf.l_margin)
            pdf.cell(pdf.epw, 6, f"TOS Badge: {tos_str}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_x(pdf.l_margin)
        pdf.cell(pdf.epw, 5, "COPY-PASTE IMAGE GENERATION PROMPT:", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font('Courier', '', 8)
        pdf.set_fill_color(248, 248, 248)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 4, prompt, border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)

    os.makedirs(os.path.dirname(output_pdf_path) or ".", exist_ok=True)
    pdf.output(output_pdf_path)
    return output_pdf_path