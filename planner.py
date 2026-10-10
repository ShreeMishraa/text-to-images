"""
Brick 2: Script -> Fine-Grained Storyboard Panel Plan.
Generates comprehensive, highly descriptive visual details for every panel
without modifying the core JSON schema or pipeline structure.
"""

import os
import json
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from parser import parse_script_to_panels

load_dotenv()


class TextOverlay(BaseModel):
    badge_type: str = Field(description="tos_yellow_pill, title_header, summary_bullet, step_header")
    text: str = Field(description="Exact on-screen text to display")


class PresenterSpec(BaseModel):
    is_present: bool = Field(description="Whether presenter is visually visible in frame")
    audio_mode: str = Field(description="SYNC, V.O., or NA")
    position: str = Field(description="center, left_third, right_third, or NA")
    dialogue: str = Field(description="Exact presenter line spoken in this frame, or NA")


class CanvasLayout(BaseModel):
    layout_mode: str = Field(description="full_bleed, presenter_with_mog_inset, split_2way, split_3way, title_card")
    visual_description: str = Field(description="Rich, highly descriptive visual composition outlining subjects, background elements, specific props, character positioning, overlays, and camera focus")


class PanelPlanItem(BaseModel):
    panel_id: int = Field(description="Sequential 1-based panel number")
    shot_type: str = Field(description="Mid Shot, FSA, MOG, Title card, Summary, Split screen, Close Up")
    scene: str = Field(description="Scene slugline e.g. INT. STUDIO - DAY or INT. CLASSROOM - DAY or EXT. RIVER PLAINS - DAY or NA")
    presenter: PresenterSpec
    canvas_layout: CanvasLayout
    text_overlays: List[TextOverlay] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list, description="Reference tags e.g. ['ref 1']")


class StoryboardPlan(BaseModel):
    title: str
    script_code: Optional[str] = None
    total_panels: int
    panels: List[PanelPlanItem]


DESCRIPTIVE_STORYBOARD_PROMPT = """
You are a master educational storyboard director. Convert the input script into a highly granular, frame-by-frame storyboard panel plan (~55 to 65 panels for a standard script).

CRITICAL DIRECTORIAL REQUIREMENTS:

1. HIGHLY DESCRIPTIVE VISUAL DETAILS:
   - Provide rich, specific visual descriptions for every single panel. Specify exact background details, foreground objects, character actions, prop labels, magnifying glass overlays, and camera framing so the image generator produces rich, informative line art.

2. SUB-ACTION BREAKDOWNS:
   - Break sequential physical actions into separate consecutive panels.

3. PROGRESSIVE BULLET BUILDS (MOG OVERLAYS):
   - Every time a list or bullet point is spoken, create a NEW panel for each added item.

4. SPLIT-SCREEN COMPARISONS:
   - When comparing items (e.g. Wet vs Dry soil, Millets vs Pulses), assign layout_mode 'split_2way' or 'split_3way' with explicit side-by-side visual notes for each section.

5. ACCURATE SCENE SLUGLINES:
   - Use proper scene slugs: INT. CLASSROOM - DAY, INT. STUDIO - DAY, EXT. RIVER PLAINS - DAY, EXT. DECCAN PLATEAU - DAY, EXT. THAR DESERT - DAY, EXT. HIMALAYAN FOOTHILLS - DAY, or NA.
"""


def plan_storyboard(parsed_doc: dict, client=None, model_name: Optional[str] = None) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_actual_api_key_here":
        return {
            "title": parsed_doc.get("title", "Storyboard Script"),
            "total_panels": 0,
            "panels": []
        }

    if client is None:
        from google import genai
        client = genai.Client(api_key=api_key)

    if model_name is None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash")

    paragraphs = parsed_doc.get("raw_paragraphs", [])
    ref_images_map = parsed_doc.get("ref_images_map", {})

    script_text = "\n".join(paragraphs)
    prompt = f"{DESCRIPTIVE_STORYBOARD_PROMPT}\n\n=== SOURCE SCRIPT ===\n{script_text}"

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": StoryboardPlan,
            "temperature": 0.2
        }
    )

    plan_dict = json.loads(response.text)

    for panel in plan_dict.get("panels", []):
        ref_paths = []
        for r in panel.get("references", []):
            clean_r = r.strip("()").lower()
            if clean_r in ref_images_map:
                ref_paths.append(ref_images_map[clean_r])
        panel["ref_image_paths"] = ref_paths

    return plan_dict