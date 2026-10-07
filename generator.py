"""
Brick 3 Prototype: PanelSpec -> Storyboard Image Generator.

Takes a single PanelSpec from Brick 2, constructs an image generation prompt deterministically
(without any LLM calls), and calls the Gemini/Imagen image generation API.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()


def build_image_prompt(panel_spec: dict) -> str:
    """
    Deterministically constructs an image prompt from a PanelSpec.
    Follows the client's approved storyboard visual language:
    - Clean black and white line-art pencil sketch style
    - Specific shot type and scene staging
    - Precise subject and environment description from canvas_layout
    - Explicit exclusions (no watermarks, no logos, no text)
    """
    layout = panel_spec.get("canvas_layout", {})
    desc = layout.get("visual_description", "")
    shot_type = panel_spec.get("shot_type", "FSA")

    # Client-approved aesthetic anchor (based on forensic reverse-engineering of approved samples)
    style_anchor = (
        "Educational storyboard illustration, clean black and white pencil sketch line-art style, "
        "crisp hand-drawn ink and graphite linework, high contrast, wide 16:9 widescreen composition."
    )

    shot_hint = f"Shot type: {shot_type}." if shot_type and shot_type != "NA" else ""

    parts = [
        style_anchor,
        shot_hint,
        desc,
        "Clean white paper background, sharp details, no text overlay, no watermark, no logo."
    ]
    return " ".join([p for p in parts if p]).strip()


def generate_panel_image(
    panel_spec: dict,
    output_path: str = "output/panel_001.png",
    model_name: str = "imagen-3.0-generate-002"
) -> str:
    """
    Generates a single storyboard image from a PanelSpec using the Gemini Image API.
    """
    from google import genai

    prompt = build_image_prompt(panel_spec)
    print(f"\nDeterministic Image Prompt:\n\"{prompt}\"\n")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is missing or contains placeholder. "
            "Please configure your valid API key in .env"
        )

    client = genai.Client(api_key=api_key)
    print(f"Calling Gemini Image API ({model_name})...")

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
        raise RuntimeError("No image was returned by the model.")

    image_bytes = result.generated_images[0].image.image_bytes
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(image_bytes)

    print(f"Successfully saved image to: {output_path}")
    return output_path


if __name__ == "__main__":
    spec_path = os.path.join("output", "sample_panel_001_spec.json")
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    print(f"Loaded PanelSpec for Panel {spec.get('panel_id')}: {spec.get('shot_type')}")
    out_img = os.path.join("output", "panel_001.png")
    generate_panel_image(spec, out_img)
