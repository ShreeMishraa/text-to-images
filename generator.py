"""
Brick 3: PanelSpec Prompt Builder & Master PDF Exporter.

Transforms parsed storyboard panel specifications into a complete,
formatted PDF prompt document without requiring image generation API calls.
"""

import os
import json
from fpdf import FPDF


def build_image_prompt(panel_spec: dict) -> str:
    """
    Deterministically constructs the client-approved line-art prompt for a panel
    based on the reverse-engineered sample_panel_001_spec.json anchor.
    """
    layout = panel_spec.get("canvas_layout", {})
    visual_desc = layout.get("visual_description", "")
    shot_type = panel_spec.get("shot_type", "FSA")

    style_anchor = (
        "Educational storyboard illustration, clean black and white pencil sketch line-art style, "
        "crisp hand-drawn ink and graphite linework, high contrast, wide 16:9 widescreen composition."
    )

    shot_hint = f"Shot type: {shot_type}." if shot_type and shot_type != "NA" else ""

    parts = [
        style_anchor,
        shot_hint,
        visual_desc,
        "Clean white paper background, sharp details, no text overlay, no watermark, no logo."
    ]
    return " ".join([p for p in parts if p]).strip()


def sanitize_text(text: str) -> str:
    """Sanitizes text strings for safe PDF rendering with standard FPDF fonts."""
    if not text:
        return "NA"
    replacements = {
        '•': '-', '–': '-', '—': '-', '“': '"', '”': '"',
        '‘': "'", '’': "'", '…': '...'
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode('latin-1', 'replace').decode('latin-1')


class StoryboardPromptPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, 'Master Storyboard Panel Prompts', 0, 1, 'C')
        self.set_font('Helvetica', 'I', 10)
        self.cell(0, 5, 'Client Approved 16:9 Line-Art Visual Specifications', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def generate_prompts_pdf(plan_data: dict, output_pdf_path: str = "output/all_storyboard_prompts.pdf") -> str:
    """
    Generates a structured PDF containing all panel details and copy-pasteable image prompts.
    """
    pdf = StoryboardPromptPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    title = sanitize_text(plan_data.get("title", "Storyboard Script"))
    panels = plan_data.get("panels", [])

    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, f"Document: {title}", 0, 1)
    pdf.cell(0, 8, f"Total Panels: {len(panels)}", 0, 1)
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
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.cell(0, 8, f" PANEL {pid:03d} | Shot: {shot_type} | Scene: {scene}", 1, 1, 'L', fill=True)

        pdf.set_font('Helvetica', '', 10)
        if dialogue != "NA":
            pdf.multi_cell(0, 5, f"Dialogue ({audio_mode}): {dialogue}")
        if visual_desc:
            pdf.multi_cell(0, 5, f"Visual Notes: {visual_desc}")

        # TOS Badges
        tos_items = panel.get("text_overlays", [])
        if tos_items:
            tos_str = " | ".join([sanitize_text(t['text'] if isinstance(t, dict) else t) for t in tos_items])
            pdf.set_font('Helvetica', 'B', 9)
            pdf.cell(0, 6, f"TOS Badge: {tos_str}", 0, 1)

        # Copy-Paste Prompt Box
        pdf.ln(2)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(0, 5, "COPY-PASTE IMAGE GENERATION PROMPT:", 0, 1)

        pdf.set_font('Courier', '', 8)
        pdf.set_fill_color(248, 248, 248)
        pdf.multi_cell(0, 4, prompt, border=1, fill=True)
        pdf.ln(6)

    os.makedirs(os.path.dirname(output_pdf_path) or ".", exist_ok=True)
    pdf.output(output_pdf_path)
    print(f"Successfully generated PDF: {output_pdf_path}")
    return output_pdf_path


def generate_panel_image(panel_spec: dict, output_path: str = "output/panel_001.png"):
    """
    Placeholder maintaining pipeline interface compatibility.
    """
    print(f"[Info] API generation bypassed. Use generate_prompts_pdf() instead.")
    return output_path


if __name__ == "__main__":
    plan_path = os.path.join("output", "v26cb09ph0601_panel_plan.json")
    if os.path.exists(plan_path):
        with open(plan_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        generate_prompts_pdf(data)