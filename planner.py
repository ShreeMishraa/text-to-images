"""
Brick 2: Script -> Fine-Grained Storyboard Panel Plan.
Enforces client-approved panelization rules (progressive builds, zoom-ins,
sub-actions, split screens, presenter cutbacks) using gemini-3.8-flash.
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
    position: str = Field(description="center, left_third, or NA")
    dialogue: str = Field(description="Exact presenter line spoken in this frame, or NA")


class CanvasLayout(BaseModel):
    layout_mode: str = Field(description="full_bleed, presenter_with_mog_inset, split_2way, split_3way, title_card")
    visual_description: str = Field(description="Rich visual composition describing characters, props, background, zoom levels, overlays, and action")


class PanelPlanItem(BaseModel):
    panel_id: int = Field(description="Sequential 1-based panel number")
    shot_type: str = Field(description="Mid Shot, FSA, MOG, Title card, Summary, Split screen, Close Up")
    scene: str = Field(description="Scene slugline e.g. INT. STUDIO - DAY or INT. CLASSROOM - DAY or NA")
    presenter: PresenterSpec
    canvas_layout: CanvasLayout
    text_overlays: List[TextOverlay] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list, description="Reference tags e.g. ['ref 1']")


class StoryboardPlan(BaseModel):
    title: str
    script_code: Optional[str] = None
    total_panels: int
    panels: List[PanelPlanItem]


FINE_GRAINED_STORYBOARD_PROMPT = """
You are a master educational storyboard director. Convert the input script into a highly granular, frame-by-frame storyboard panel plan (~55 to 65 panels for a standard script).

STRICT PANELIZATION RULES (CRITICAL FOR CLIENT APPROVAL):

1. SUB-ACTION BREAKDOWNS:
   - Break sequential physical actions into separate consecutive panels.
   - Example: "Three kids taking seeds" MUST become 3 panels:
     * Panel 1: Close Up of Kid 1 taking seeds from a glass jar.
     * Panel 2: Close Up of Kid 2 taking seeds from a glass jar.
     * Panel 3: Close Up of Kid 3 taking seeds from a glass jar.
     * Panel 4: Wide Shot showing all 3 kids planting seeds into 3 labeled pots.

2. PROGRESSIVE BULLET BUILDS (MOG OVERLAYS):
   - Every time a list or bullet point is spoken, create a NEW panel for each added item.
   - Panel N: Shows item 1.
   - Panel N+1: Shows item 1 + item 2 added.
   - Panel N+2: Shows item 1 + item 2 + item 3 added, etc.

3. VISUAL STATE ANIMATIONS (ZOOM / MAGNIFYING GLASS / OVERLAYS):
   - Break visual explanations into step-by-step camera moves.
   - Example: Base landscape (Panel A) -> Camera Zoom-in (Panel B) -> Magnifying Glass overlay (Panel C) -> Particle/Icon overlay (Panel D) -> Transition to MOG (Panel E).

4. SPLIT-SCREEN COMPARISONS:
   - When comparing items (e.g. Wet vs Dry soil, Millets vs Pulses, 3 watering pots), assign layout_mode 'split_2way' or 'split_3way' with explicit multi-frame descriptions.

5. PRESENTER CUTBACKS:
   - Every time the presenter addresses the camera directly in SYNC audio without a MOG inset or FSA graphic, output a dedicated 'Mid Shot' presenter panel in the studio.

6. RICH VISUAL DESCRIPTIONS:
   - Explicitly detail characters (teacher in sari, students in uniform, detective in trench coat), environment (blackboard, laboratory table, studio background), props (clay pots with front labels 'DARK SOIL', 'RED SOIL', 'SANDY SOIL'), and action.
"""


def plan_storyboard(parsed_doc: dict, client=None, model_name: Optional[str] = None) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_actual_api_key_here":
        # Fallback if no API key
        return {
            "title": parsed_doc.get("title", "Storyboard Script"),
            "total_panels": 0,
            "panels": []
        }

    if client is None:
        from google import genai
        client = genai.Client(api_key=api_key)

    if model_name is None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    paragraphs = parsed_doc.get("raw_paragraphs", [])
    ref_images_map = parsed_doc.get("ref_images_map", {})

    script_text = "\n".join(paragraphs)
    prompt = f"{FINE_GRAINED_STORYBOARD_PROMPT}\n\n=== SOURCE SCRIPT ===\n{script_text}"

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

    # Attach extracted ref image paths to panels
    for panel in plan_dict.get("panels", []):
        ref_paths = []
        for r in panel.get("references", []):
            clean_r = r.strip("()").lower()
            if clean_r in ref_images_map:
                ref_paths.append(ref_images_map[clean_r])
        panel["ref_image_paths"] = ref_paths

    return plan_dict