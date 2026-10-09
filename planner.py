"""
Brick 2: Script -> Client-Approved Storyboard Panel Plan.

Transforms parsed script data from Brick 1 into a structured, distinct storyboard panel plan
using ONE structured GenAI reasoning call adhering to client visual rules.
"""

import os
import json
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from parser import parse_script, parse_script_to_panels

load_dotenv()


class VectorAnnotation(BaseModel):
    type: str = Field(description="Annotation type: arrow, cross_mark, circle_highlight, etc.")
    direction: Optional[str] = Field(default="none", description="Direction: left, right, up, down, circular, none")
    color: Optional[str] = Field(default=None, description="Color token: red, blue, cyan, gold, etc.")
    label: Optional[str] = Field(default=None, description="Visible text on the arrow/annotation")
    meaning: Optional[str] = Field(default=None, description="Semantic concept e.g. friction_opposing, applied_force, gravity")


class TextOverlay(BaseModel):
    badge_type: str = Field(description="tos_yellow_pill, title_header, summary_bullet, step_header")
    text: str = Field(description="Exact on-screen text to display")
    position: Optional[str] = Field(default="bottom_center", description="bottom_center, inset_bottom, screen_center")


class PresenterSpec(BaseModel):
    is_present: bool = Field(description="Whether presenter is visually visible in this frame")
    audio_mode: str = Field(description="SYNC, V.O., or NA")
    position: str = Field(description="center, left_third, or NA")
    dialogue: str = Field(description="Exact presenter line spoken in this frame, or NA")


class CanvasLayout(BaseModel):
    layout_mode: str = Field(description="full_bleed, presenter_with_mog_inset, split_2way, split_3way, title_card")
    primary_subject: str = Field(description="Main subject of the frame")
    visual_description: str = Field(description="Detailed visual composition for future image generation")
    visual_state_delta: str = Field(description="What makes this panel distinct from previous panel")


class PanelPlanItem(BaseModel):
    panel_id: int = Field(description="Sequential 1-based panel number")
    shot_type: str = Field(description="Mid Shot, FSA, MOG, Title card, Summary, Split screen")
    scene: str = Field(description="Scene slugline e.g. INT. STUDIO - DAY or NA")
    presenter: PresenterSpec
    canvas_layout: CanvasLayout
    vector_annotations: List[VectorAnnotation] = Field(default_factory=list)
    text_overlays: List[TextOverlay] = Field(default_factory=list)
    continuity_ref: Optional[str] = Field(default=None, description="Anchor ID to previous asset if reusable")


class StoryboardPlan(BaseModel):
    title: str
    script_code: Optional[str] = None
    total_panels: int
    panels: List[PanelPlanItem]


CLIENT_VISUAL_RULES_PROMPT = """
You are a senior storyboard director converting an educational script into a client-approved frame-by-frame storyboard panel plan.

FOLLOW THE REVERSE-ENGINEERED CLIENT VISUAL RULES STRICTLY:
1. PANELIZATION LOGIC:
   - Every distinct visual beat, delta, or state change MUST be its own panel.
   - Do NOT merge sequential visual steps.
   - Do NOT create redundant duplicate panels.
2. SHOT TYPES & GEOMETRY:
   - 'Mid Shot': Presenter centered in studio, talking directly to camera (SYNC audio).
   - 'MOG': Presenter positioned on LEFT THIRD; rectangular 4:3 visual window on RIGHT.
   - 'FSA' (Full Screen Animation): Standalone diagram, split-screen, or full illustration. Presenter is ABSENT (V.O. audio).
   - 'Title card' / 'Summary': Standalone full screen title graphic.
3. ARROWS & ANNOTATIONS:
   - Applied force = Blue straight arrow pointing in motion direction.
   - Friction = Red straight arrow pointing strictly OPPOSITE to motion direction.
4. ON-SCREEN TEXT (TOS):
   - Preserve exact wording from script for TOS.
"""


def _compress_script_for_llm(parsed_doc: dict) -> str:
    """
    Extracts visually meaningful parts of the script to minimize token consumption.
    Handles both raw element formats and pre-parsed panel formats.
    """
    lines = []
    file_name = parsed_doc.get("file_name") or parsed_doc.get("title", "Script")
    lines.append(f"# SCRIPT: {file_name}")

    if "elements" in parsed_doc:
        for el in parsed_doc.get("elements", []):
            if el.get("type") == "table":
                lines.append("## METADATA:")
                for row in el.get("rows", []):
                    if len(row) >= 2:
                        k, v = row[0].strip(), row[1].strip()
                        if any(term in k.lower() for term in ["title", "code", "character", "location", "costume", "animated"]):
                            lines.append(f"- **{k}**: {v}")
            elif el.get("type") == "paragraph":
                text = el.get("text", "").strip()
                if text:
                    links = el.get("links", [])
                    link_info = " " + " ".join([f"[{l.get('text', 'ref')}]({l.get('url', '')})" for l in links]) if links else ""
                    lines.append(f"{text}{link_info}")

    elif "panels" in parsed_doc:
        for p in parsed_doc.get("panels", []):
            desc = p["canvas_layout"]["visual_description"]
            diag = p["presenter"]["dialogue"]
            lines.append(f"Panel {p['panel_id']}: {desc} | Dialogue: {diag}")

    return "\n".join(lines)


def plan_storyboard(parsed_script: dict, client=None, model_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates structured storyboard plan via Gemini API, or falls back to
    deterministic parser if API key is not supplied.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_actual_api_key_here":
        print("GEMINI_API_KEY not configured. Utilizing deterministic parser fallback...")
        if "file_name" in parsed_script and os.path.exists(os.path.join("input", parsed_script["file_name"])):
            return parse_script_to_panels(os.path.join("input", parsed_script["file_name"]))
        return parsed_script

    compressed_script = _compress_script_for_llm(parsed_script)

    if client is None:
        from google import genai
        client = genai.Client(api_key=api_key)

    if model_name is None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    prompt = f"{CLIENT_VISUAL_RULES_PROMPT}\n\n=== SOURCE SCRIPT ===\n{compressed_script}"

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
    return plan_dict


def validate_plan(plan_dict: dict) -> bool:
    """Validates uniqueness of panel IDs and structural keys."""
    if "panels" not in plan_dict or not isinstance(plan_dict["panels"], list):
        raise ValueError("Plan must contain a 'panels' array")

    panels = plan_dict["panels"]
    if len(panels) == 0:
        raise ValueError("Plan contains 0 panels")

    seen_ids = set()
    last_id = 0

    for idx, p in enumerate(panels):
        pid = p.get("panel_id")
        if pid is None or not isinstance(pid, int):
            raise ValueError(f"Panel at index {idx} has invalid panel_id: {pid}")
        if pid in seen_ids:
            raise ValueError(f"Duplicate panel_id detected: {pid}")
        if pid <= last_id:
            raise ValueError(f"Panel IDs are not strictly increasing: {pid} after {last_id}")
        seen_ids.add(pid)
        last_id = pid

    return True