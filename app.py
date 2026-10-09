import os
import json
import streamlit as st
from parser import parse_script_to_panels
from generator import generate_panel_image

st.set_page_config(page_title="AI Storyboard Generator", layout="wide")
st.title("🎬 Educational Storyboard Pipeline")
st.write("Upload the script (.docx) and the visual reference file (.pdf) to parse panels and generate line-art sketches.")

input_dir = "input"
output_dir = "output"
os.makedirs(input_dir, exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# --- DUAL FILE UPLOADERS ---
st.sidebar.header("📁 Mandatory Client Files")

uploaded_script = st.sidebar.file_uploader("1. Script Document (.docx)", type=["docx"])
uploaded_ref_pdf = st.sidebar.file_uploader("2. Visual Reference PDF (.pdf)", type=["pdf"])

script_saved_path = None
ref_pdf_saved_path = None

if uploaded_script:
    script_saved_path = os.path.join(input_dir, uploaded_script.name)
    with open(script_saved_path, "wb") as f:
        f.write(uploaded_script.getbuffer())
    st.sidebar.success(f"Loaded Script: {uploaded_script.name}")

if uploaded_ref_pdf:
    ref_pdf_saved_path = os.path.join(input_dir, uploaded_ref_pdf.name)
    with open(ref_pdf_saved_path, "wb") as f:
        f.write(uploaded_ref_pdf.getbuffer())
    st.sidebar.success(f"Loaded Ref PDF: {uploaded_ref_pdf.name}")

# --- PARSE AND PLAN ---
if script_saved_path:
    if st.sidebar.button("🚀 Parse & Map Visual References"):
        with st.spinner("Extracting script dialogue and reference IMAGES from PDF..."):
            panel_data = parse_script_to_panels(script_saved_path, ref_pdf_saved_path)
            plan_file = os.path.join(output_dir, "v26cb09ph0601_panel_plan.json")
            with open(plan_file, "w", encoding="utf-8") as f:
                json.dump(panel_data, f, indent=2)

        st.success(f"Parsed {panel_data['total_panels']} panels and mapped visual reference images!")

# --- DISPLAY STORYBOARD ---
plan_path = os.path.join(output_dir, "v26cb09ph0601_panel_plan.json")
if os.path.exists(plan_path):
    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    panels = data.get("panels", [])

    st.subheader("🖼️ Test Batch Generation")
    if st.button("Generate First 5 Images in One Go"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        MAX_BATCH = 5
        generated_count = 0

        for panel in panels:
            pid = panel["panel_id"]
            img_path = os.path.join(output_dir, f"panel_{pid:03d}.png")

            if os.path.exists(img_path):
                continue

            if generated_count >= MAX_BATCH:
                st.info("Capped at 5 images for this test batch.")
                break

            status_text.text(f"Rendering Panel {pid:03d} ({generated_count + 1}/{MAX_BATCH})...")

            try:
                generate_panel_image(panel, img_path)
                generated_count += 1
                progress_bar.progress(generated_count / MAX_BATCH)
            except Exception as e:
                st.error(f"Error on Panel {pid:03d}: {e}")
                break

        if generated_count > 0:
            st.success(f"Rendered {generated_count} new images!")
            st.rerun()
        else:
            st.info("First 5 panel images are already generated.")

    st.divider()
    st.subheader("📋 Client Approved Storyboard Comparison Grid")

    for panel in panels:
        pid = panel["panel_id"]
        img_path = os.path.join(output_dir, f"panel_{pid:03d}.png")
        ref_imgs = panel.get("ref_image_paths", [])

        st.markdown(f"### Panel {pid:03d} — {panel['shot_type']} ({panel['scene']})")

        c1, c2, c3 = st.columns([1, 1, 1])

        # Column 1: Client Reference Image
        with c1:
            st.write("**Client Reference Image:**")
            if ref_imgs and os.path.exists(ref_imgs[0]):
                st.image(ref_imgs[0], caption=f"Extracted Reference ({panel['references'][0]})")
            else:
                st.caption("No reference image tag attached.")

        # Column 2: Generated AI Sketch
        with c2:
            st.write("**Generated AI Sketch:**")
            if os.path.exists(img_path):
                st.image(img_path, caption=f"Generated Panel {pid:03d}")
            else:
                st.info(f"Pending generation.")
                if st.button(f"Render Panel {pid:03d}", key=f"btn_{pid}"):
                    try:
                        generate_panel_image(panel, img_path)
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        # Column 3: Text & TOS Badges
        with c3:
            st.write("**Script Details:**")
            if panel["presenter"]["dialogue"] != "NA":
                st.markdown(f"**Dialogue ({panel['presenter']['audio_mode']}):** {panel['presenter']['dialogue']}")
            if panel["canvas_layout"]["visual_description"]:
                st.markdown(f"**Visual:** {panel['canvas_layout']['visual_description']}")
            if panel["text_overlays"]:
                tos_items = [t['text'] if isinstance(t, dict) else t for t in panel["text_overlays"]]
                st.warning(f"**TOS Badge:** {' | '.join(tos_items)}")

        st.divider()