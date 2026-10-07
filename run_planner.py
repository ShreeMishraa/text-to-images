"""
CLI runner for Brick 2 Storyboard Planner.
Executes the single GenAI call on an input script and saves the structured plan JSON.
"""

import sys
import os
import json
from parser import parse_script
from planner import plan_storyboard, validate_plan


def main():
    if len(sys.argv) < 2:
        input_file = os.path.join("input", "v26cb09ph0601.docx")
        if not os.path.exists(input_file):
            input_file = os.path.join("input", "v26cb07ge0110.pdf")
    else:
        input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    print(f"Ingesting script: {input_file}")
    parsed_doc = parse_script(input_file)
    print(f"Extracted {parsed_doc['total_elements']} elements.")

    print("\nCalling GenAI Model for Storyboard Planning (Single Call)...")
    try:
        plan = plan_storyboard(parsed_doc)
    except Exception as e:
        print(f"\n[Error calling GenAI API]: {e}")
        print("\nPlease ensure a valid GEMINI_API_KEY is configured in your .env file.")
        sys.exit(1)

    print("\nValidating generated panel plan...")
    validate_plan(plan)
    print("Validation passed successfully!")

    total_panels = len(plan.get("panels", []))
    print(f"\nGenerated {total_panels} distinct storyboard panels.")

    # Save output
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    out_file = os.path.join(output_dir, f"{base_name}_panel_plan.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    print(f"Saved complete panel plan to: {out_file}")

    # Report token usage
    usage = plan.get("_usage_metadata", {})
    if usage:
        print("\n--- TOKEN USAGE ---")
        print(f"Prompt Tokens:     {usage.get('prompt_tokens', 'N/A')}")
        print(f"Output Tokens:     {usage.get('output_tokens', 'N/A')}")
        print(f"Total Tokens:      {usage.get('total_tokens', 'N/A')}")


if __name__ == "__main__":
    main()
