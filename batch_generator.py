"""
Free-Tier Batch Image Generator (5 Images per run).
"""

import os
import sys
import json
import time
from generator import generate_panel_image

PLAN_FILE = os.path.join("output", "v26cb09ph0601_panel_plan.json")
OUTPUT_DIR = "output"
DAILY_REQUEST_LIMIT = 5  # Strict 5-image cap per run


def run_batch_generation():
    if not os.path.exists(PLAN_FILE):
        print(f"Plan file not found: {PLAN_FILE}")
        print("Running deterministic parser to create default plan...")
        from parser import parse_script_to_panels
        input_docx = os.path.join("input", "v26cb09ph0601.docx")
        if os.path.exists(input_docx):
            plan_data = parse_script_to_panels(input_docx)
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            with open(PLAN_FILE, "w", encoding="utf-8") as f:
                json.dump(plan_data, f, indent=2)
        else:
            print("No input document found in input/")
            sys.exit(1)

    with open(PLAN_FILE, "r", encoding="utf-8") as f:
        plan = json.load(f)

    panels = plan.get("panels", [])
    total_panels = len(panels)
    print(f"Loaded plan containing {total_panels} total panels.")

    completed_today = 0

    for panel in panels:
        panel_id = panel.get("panel_id")
        output_image_path = os.path.join(OUTPUT_DIR, f"panel_{panel_id:03d}.png")

        if os.path.exists(output_image_path):
            print(f"[SKIP] Panel {panel_id:03d} already exists.")
            continue

        if completed_today >= DAILY_REQUEST_LIMIT:
            print(f"\n[BATCH LIMIT REACHED] Generated {completed_today} images in this session.")
            break

        print(f"\n[RENDERING {completed_today + 1}/{DAILY_REQUEST_LIMIT}] Panel {panel_id:03d} of {total_panels}...")
        try:
            generate_panel_image(
                panel_spec=panel,
                output_path=output_image_path
            )
            completed_today += 1
            time.sleep(4)  # 4-second safety buffer between requests

        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Panel {panel_id:03d}: {error_msg}")
            if "429" in error_msg or "ResourceExhausted" in error_msg or "quota" in error_msg.lower():
                print("\n[QUOTA EXCEEDED] Reached daily API limit.")
                break

    existing = len([p for p in panels if os.path.exists(os.path.join(OUTPUT_DIR, f"panel_{p['panel_id']:03d}.png"))])
    print(f"\nSession finished. Total ready: {existing}/{total_panels} images in '{OUTPUT_DIR}/'.")


if __name__ == "__main__":
    run_batch_generation()