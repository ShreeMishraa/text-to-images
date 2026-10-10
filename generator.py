"""
Brick 3: Master Prompt Builder & PDF Exporter.
Constructs line-art pencil sketch prompts with color scrubbing and layout enforcement.
Outputs master prompt PDF (output/all_storyboard_prompts.pdf).
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


def scrub_color_words(text: str) -> str:
    """Removes color adjectives to prevent AI models from generating color fills."""
    color_map = {
        r'\bgreen sari\b': 'patterned traditional sari',
        r'\bgreen plastic watering can\b': 'watering can',
        r'\bgreen\b': 'lush',
        r'\breddish-brown\b': 'granular',
        r'\breddish-ochre\b': 'iron-rich',
        r'\breddish\b': 'granular',
        r'\bred\b': 'terracotta',
        r'\byellowish-grey\b': 'grained',
        r'\byellow\b': 'grained',
        r'\bblue sky\b': 'clear sky',
        r'\bblue\b': 'clear',
        r'\bgolden\b': 'ripe',
        r'\bgold\b': 'ripe',
        r'\bdark grey-charcoal\b': 'dark',
        r'\bterracotta red\b': 'terracotta'
    }
    for pattern, repl in color_map.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def build_image_prompt(panel_spec: dict) -> str:
    layout = panel_spec.get("canvas_layout", {})
    vis_desc = layout.get("visual_description", "")
    shot_type = panel_spec.get("shot_type", "FSA")
    layout_mode = layout.get("layout_mode", "full_bleed")

    # Scrub color words to enforce pure line art
    vis_desc_scrubbed = scrub_color_words(vis_desc)

    # 1. Base Line-Art Aesthetic Anchor
    style_anchor = (
        "STRICT MONOCHROME GRAYSCALE, pure black and white line-art pencil sketch, "
        "crisp hand-drawn ink and graphite linework, fine hatching and cross-hatching, "
        "high contrast, 16:9 widescreen composition, clean white paper background, "
        "zero color fill, no color shading, no color gradients."
    )

    # 2. Layout & Framing Directives
    layout_directive = ""
    if layout_mode == "split_3way" or "3-way" in vis_desc_scrubbed.lower() or "three-way" in vis_desc_scrubbed.lower():
        layout_directive = (
            "Composition: 3-way vertical split screen layout with three equal side-by-side vertical panels "
            "separated by clean, straight thin black dividing border lines."
        )
    elif layout_mode == "split_2way" or "split" in vis_desc_scrubbed.lower():
        layout_directive = (
            "Composition: 2-way vertical split screen layout with two equal side-by-side vertical panels "
            "separated by a clean, straight thin black dividing border line."
        )
    elif layout_mode == "presenter_with_mog_inset":
        layout_directive = (
            "Composition: Presenter standing on the left third of the screen in studio; "
            "a rectangular 4:3 graphic inset window on the right third displaying line-art illustration."
        )
    elif shot_type == "Mid Shot":
        layout_directive = "Composition: Mid shot framing, presenter standing centered in studio addressing camera."
    else:
        layout_directive = f"Shot framing: {shot_type}."

    # 3. Contextual Visual Anchors
    scene_context = ""
    vis_lower = vis_desc_scrubbed.lower()

    if any(k in vis_lower for k in ["classroom", "pot", "soil", "plant", "seed", "water", "dark soil"]):
        scene_context = (
            "Setting: Indian classroom interior with a large blackboard in background reading 'SOIL EXPERIMENT - PLANT GROWTH' and educational posters on walls. "
            "Characters: Indian female teacher in traditional sari and Indian school children wearing neat school uniforms. "
            "Props: Terracotta clay pots resting on a wooden table with printed front labels 'DARK SOIL', 'RED SOIL', 'SANDY SOIL'."
        )
    elif any(k in vis_lower for k in ["detective", "artifact", "cylinder", "weighing balance", "density", "beaker"]):
        scene_context = (
            "Setting: Detective study room with a wooden table containing a glass measuring cylinder filled with water, "
            "beaker, thread, and digital scale. Background: Cork board with suspect photos connected by string. "
            "Characters: Presenter wearing a detective trench coat and holding a magnifying glass."
        )
    elif "alluvial" in vis_lower:
        scene_context = "Setting: Wide river plains with river sediment depositing, active alluvial soil, rice paddies and wheat fields, distant Himalayan foothills."
    elif "black soil" in vis_lower or "cotton" in vis_lower:
        scene_context = "Setting: Deccan traps basalt plateau landscape, dark soil with deep dry cracks, mature cotton plants with white cotton bolls."
    elif "red soil" in vis_lower or "millet" in vis_lower:
        scene_context = "Setting: Dry peninsular hills landscape, iron-rich granular soil, pearl millet and pigeon pea crops growing."
    elif "laterite" in vis_lower or "tea" in vis_lower:
        scene_context = "Setting: High-rainfall hilly slopes with terraced tea and coffee plantations, misty rain-shrouded peaks, leached coarse soil."
    elif "desert soil" in vis_lower or "sandy land" in vis_lower:
        scene_context = "Setting: Arid desert landscape with dry riverbed, wind-blown sand sheets, sparse drought-resistant bajra millet crops."
    elif "mountain" in vis_lower or "alpine" in vis_lower or "terrace" in vis_lower:
        scene_context = "Setting: Snow-capped Himalayan alpine peaks, terraced hillside contour farming with apple fruit orchards and fast-flowing mountain stream."

    prompt_parts = [
        style_anchor,
        layout_directive,
        scene_context,
        f"Visual Action: {vis_desc_scrubbed}",
        "No color, no watercolor, no digital color render, no watermark, no logo, no text overlay outside specified labels."
    ]

    return " ".join([p for p in prompt_parts if p]).strip()


class StoryboardPromptPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 14)
        self.cell(self.epw, 10, 'Master Storyboard Panel Prompts', border=0, new_x="LMARGIN", new_y="NEXT", align='C')
        self.set_font('Helvetica', 'I', 10)
        self.cell(self.epw, 5, 'Client Approved 16:9 Line-Art Visual Specifications', border=0, new_x="LMARGIN", new_y="NEXT", align='C')
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