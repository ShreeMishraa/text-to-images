import os
import json
from parser import parse_script
from planner import _compress_script_for_llm, validate_plan, StoryboardPlan


def test_compress_script():
    parsed = parse_script(os.path.join("input", "v26cb09ph0601.docx"))
    compressed = _compress_script_for_llm(parsed)
    assert "Friction" in compressed
    assert "FADE IN:" in compressed
    assert "v26cb09ph0601_dr" in compressed
    # Ensure non-visual fields like SME or Writer are omitted from compressed view
    assert "Avijit Kundu" not in compressed
    print(f"PASS: Script compression reduced {len(str(parsed))} chars to {len(compressed)} chars.")


def test_validate_plan():
    # Test valid dummy plan matching StoryboardPlan schema
    dummy_plan = {
        "title": "Test Title",
        "total_panels": 2,
        "panels": [
            {
                "panel_id": 1,
                "shot_type": "FSA",
                "scene": "NA",
                "presenter": {
                    "is_present": False,
                    "audio_mode": "V.O.",
                    "position": "NA",
                    "dialogue": "Introduction line"
                },
                "canvas_layout": {
                    "layout_mode": "full_bleed",
                    "primary_subject": "Park scene",
                    "visual_description": "2D park animation with kids",
                    "visual_state_delta": "Opening establishing shot"
                },
                "vector_annotations": [],
                "text_overlays": []
            },
            {
                "panel_id": 2,
                "shot_type": "Mid Shot",
                "scene": "INT. STUDIO - DAY",
                "presenter": {
                    "is_present": True,
                    "audio_mode": "SYNC",
                    "position": "center",
                    "dialogue": "Hello viewers"
                },
                "canvas_layout": {
                    "layout_mode": "full_bleed",
                    "primary_subject": "Presenter in studio",
                    "visual_description": "Presenter addressing camera",
                    "visual_state_delta": "Cut to studio presenter"
                },
                "vector_annotations": [],
                "text_overlays": []
            }
        ]
    }
    assert validate_plan(dummy_plan) is True
    print("PASS: Plan validation succeeded.")

    # Test error handling: duplicate panel IDs
    invalid_plan = dict(dummy_plan)
    invalid_plan["panels"] = [
        dummy_plan["panels"][0],
        dict(dummy_plan["panels"][0])  # Duplicate panel_id 1
    ]
    try:
        validate_plan(invalid_plan)
        assert False, "Should have raised ValueError on duplicate ID"
    except ValueError as e:
        assert "Duplicate panel_id" in str(e)
        print("PASS: Duplicate panel detection caught correctly.")


if __name__ == "__main__":
    test_compress_script()
    test_validate_plan()
    print("ALL PLANNER UNIT TESTS PASSED.")
