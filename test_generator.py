import os
import json
from generator import build_image_prompt


def test_build_image_prompt():
    spec_path = os.path.join("output", "sample_panel_001_spec.json")
    assert os.path.exists(spec_path), f"Spec file not found: {spec_path}"

    with open(spec_path, "r", encoding="utf-8") as f:
        spec = json.load(f)

    prompt = build_image_prompt(spec)
    assert len(prompt) > 50
    assert "pencil sketch line-art style" in prompt
    assert "FSA" in prompt
    assert "park" in prompt
    assert "no watermark" in prompt
    print(f"PASS: Deterministic prompt built ({len(prompt)} chars, 0 LLM calls):")
    print(f"\"{prompt[:90]}...\"")


def test_output_image_exists():
    out_img = os.path.join("output", "panel_001.png")
    assert os.path.exists(out_img), f"Output image not found: {out_img}"
    size_kb = os.path.getsize(out_img) / 1024
    assert size_kb > 50, f"Image file is suspiciously small: {size_kb} KB"
    print(f"PASS: output/panel_001.png exists ({size_kb:.1f} KB).")


if __name__ == "__main__":
    test_build_image_prompt()
    test_output_image_exists()
    print("ALL BRICK 3 PROTOTYPE TESTS PASSED.")
