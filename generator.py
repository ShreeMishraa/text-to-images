"""
Brick 3: PanelSpec -> Storyboard Image Generator.

Transforms a PanelSpec dictionary from planner.py into a high-contrast line-art 
storyboard image using Google's Imagen model via the official google-genai SDK.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()


def build_image_prompt(panel_spec: dict) -> str:
    """
    Deterministically constructs an image prompt adhering to the client-approved 
    visual language and reverse-engineered style anchors.
    """
    layout = panel_spec.get("canvas_layout", {})
    visual_desc = layout.get("visual_description", "")
    shot_type = panel_spec.get("shot_type", "FSA")

    # Client-Approved Aesthetic Anchor
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


def generate_panel_image(
    panel_spec: dict,
    output_path: str = "output/panel_001.png",
    model_name: str = None
) -> str:
    """
    Generates a single storyboard panel image using the official Google GenAI SDK.
    """
    from google import genai

    if model_name is None:
        model_name = os.getenv("IMAGEN_MODEL", "imagen-3.0-generate-002")

    prompt = build_image_prompt(panel_spec)
    print(f"\n[GENERATING IMAGE] Prompt:\n\"{prompt}\"\n")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_actual_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is missing or contains placeholder. "
            "Please configure your key in .env"
        )

    client = genai.Client(api_key=api_key)

    result = client.models.generate_images(
        model=model_name,
        prompt=prompt,
        config=dict(
            number_of_images=1,
            aspect_ratio="16:9",
            output_mime_type="image/png"
        )
    )

    if not result.generated_images:
        raise RuntimeError("No image returned from Gemini/Imagen API.")

    image_bytes = result.generated_images[0].image.image_bytes
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    print(f"Successfully saved image: {output_path}")
    return output_path


if __name__ == "__main__":
    spec_path = os.path.join("output", "sample_panel_001_spec.json")
    if os.path.exists(spec_path):
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
        out_img = os.path.join("output", "panel_001.png")
        generate_panel_image(spec, out_img)
    else:
        print(f"Spec file not found: {spec_path}")