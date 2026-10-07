"""
Brick 2: Script -> Client-Approved Storyboard Panel Plan.

Transforms parsed script data from Brick 1 into a structured, distinct storyboard panel plan
using ONE structured GenAI reasoning call adhering to the reverse-engineered client visual rules.
"""

import os
import json
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from parser import parse_script

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
    is_present: bool = Field(description="Whether the presenter is visually visible in this frame")
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
   - Do NOT merge sequential visual steps. For example:
     * Introducing a force arrow is Panel N; introducing the opposing friction arrow is Panel N+1.
     * Posing a question/scenario is Panel N; revealing the answer or stamping a red cross (X) on an error is Panel N+1.
     * Accumulating split-screen comparisons: 1st example is Panel N; 2-way split is Panel N+1; 3-way split is Panel N+2.
   - Do NOT create redundant duplicate panels where no visual element, text, or gesture changes.
   - Average pacing is ~8-12 words per panel.

2. SHOT TYPES & GEOMETRY:
   - 'Mid Shot': Presenter centered in studio, talking directly to camera (SYNC audio).
   - 'MOG': Presenter positioned on LEFT THIRD; rectangular 4:3 visual window on RIGHT.
   - 'FSA' (Full Screen Animation): Standalone diagram, split-screen, or full illustration. Presenter is ABSENT (V.O. audio).
   - 'Title card' / 'Summary': Standalone full screen title/summary graphic. Presenter is ABSENT (audio NA).

3. ARROWS & ANNOTATIONS:
   - Arrows are semantic:
     * Motion / Applied force = Blue or gray straight arrow pointing in motion direction.
     * Friction = Red straight arrow pointing strictly OPPOSITE to motion direction.
     * Weight (Gravity) = Red vertical arrow pointing down.
     * Normal Force = Cyan/blue vertical arrow pointing up.
   - Misconceptions / Incorrect actions get a bold red cross mark ('cross_mark') overlaid.

4. ON-SCREEN TEXT (TOS):
   - Preserve exact wording from the script for TOS. Do NOT paraphrase or shorten.
   - All TOS badges are 'tos_yellow_pill' placed at bottom.

5. DIALOGUE & SYNC:
   - If audio cue is PRESENTER: audio_mode is 'SYNC', presenter is visible.
   - If audio cue is PRESENTER (V.O.): audio_mode is 'V.O.', presenter is usually absent (FSA) or in MOG.
   - For title/summary cards without dialogue, dialogue is 'NA'.

Return valid JSON adhering to the StoryboardPlan schema.
"""


def _compress_script_for_llm(parsed_doc: dict) -> str:
    """
    Extracts only visually meaningful parts of the script to minimize token consumption.
    Strips non-visual metadata (sign-offs, word counts) while preserving cues, dialogue, and tables.
    """
    lines = []
    lines.append(f"# SCRIPT: {parsed_doc.get('file_name')}")
    
    for el in parsed_doc.get("elements", []):
        el_type = el.get("type")
        if el_type == "table":
            lines.append("## METADATA:")
            for row in el.get("rows", []):
                if len(row) >= 2:
                    k, v = row[0].strip(), row[1].strip()
                    # Filter for visually relevant metadata only
                    if any(term in k.lower() for term in ["title", "code", "character", "location", "costume", "props", "animated"]):
                        lines.append(f"- **{k}**: {v}")
        elif el_type == "paragraph":
            text = el.get("text", "").strip()
            if text:
                # Append links if present
                links = el.get("links", [])
                if links:
                    link_info = " " + " ".join([f"[{l.get('text', 'ref')}]({l.get('url', '')})" for l in links])
                    lines.append(f"{text}{link_info}")
                else:
                    lines.append(text)
                    
    return "\n".join(lines)


def plan_storyboard(parsed_script: dict, client=None, model_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes ONE structured GenAI reasoning call to generate the storyboard panel plan.
    """
    compressed_script = _compress_script_for_llm(parsed_script)

    if client is None:
        from google import genai
        client = genai.Client()

    if model_name is None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    prompt = f"{CLIENT_VISUAL_RULES_PROMPT}\n\n=== SOURCE SCRIPT ===\n{compressed_script}"

    # Call Gemini with structured output
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_schema": StoryboardPlan,
            "temperature": 0.2
        }
    )

    # Parse JSON
    plan_dict = json.loads(response.text)

    # Attach token tracking metrics if available
    usage = {}
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        usage = {
            "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", None),
            "output_tokens": getattr(response.usage_metadata, "candidates_token_count", None),
            "total_tokens": getattr(response.usage_metadata, "total_token_count", None)
        }
    plan_dict["_usage_metadata"] = usage

    return plan_dict


def validate_plan(plan_dict: dict) -> bool:
    """
    Basic deterministic validation:
    - Valid schema
    - Non-empty panels
    - Unique and strictly ordered panel IDs
    - Required core fields present on all panels
    """
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

        # Check required fields
        for field in ["shot_type", "scene", "presenter", "canvas_layout"]:
            if field not in p:
                raise ValueError(f"Panel {pid} missing required field: {field}")

    return True
