"""
CHAT Report Generation App
Generates CHAT reports using Groq (Llama).
"""

import streamlit as st
import time

from data_utils import load_data, filter_data, calculate_stats
from providers import check_api_keys, PROVIDERS
from prompts import generate_all_sections
from report_builder import generate_pdf_report

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CHAT Report Generator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)



# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.title("CHAT Report Generator")
    st.caption("Climate Health Vulnerability Assessment Tool")

    # Data Filters
    st.subheader("Data Filters")
    df = load_data()
    states = sorted(df['state'].dropna().unique().tolist())
    selected_state = st.selectbox("State", states, index=0)

    state_df = df[df['state'].str.contains(selected_state, case=False, na=False)]
    lgas = ["All"] + sorted(state_df['lga'].dropna().unique().tolist())
    selected_lga = st.selectbox("LGA", lgas, index=0)

    st.divider()

    # Report Depth
    # Comprehensive    = full report with tables, charts, and all narrative sections.
    # Moderate         = narrative-only report (no tables/charts/roadmap).
    # Overview Summary = single consolidated narrative, one paragraph.
    st.subheader("Report Depth")
    report_depth = st.radio("Depth", ["Comprehensive", "Moderate", "Overview Summary"], index=0)

# ============================================================
# PREPARE DATA
# ============================================================

filtered_df = filter_data(df, state=selected_state, lga=selected_lga if selected_lga != "All" else None)

location_name = selected_state
location_type = "State"
if selected_lga and selected_lga != "All":
    location_name = f"{selected_lga}, {selected_state}"
    location_type = "LGA"

context = {
    'location_name': location_name,
    'location_type': location_type,
    'state': selected_state,
    'lga': selected_lga if selected_lga != "All" else None,
}

stats = calculate_stats(filtered_df, context)

# ============================================================
# MAIN CONTENT
# ============================================================

st.header(f"Generate Report — {location_name}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Facilities", stats['facilities'])
with col2:
    st.metric("Assessments", f"{stats['total']:,}")
with col3:
    st.metric("Vulnerability Index", f"{stats['avg_vuln']}/3.0")

st.divider()

api_status = check_api_keys()

if st.button("Generate Report", type="primary", width="stretch"):
    if not api_status.get("groq"):
        st.error("Groq API key not configured. Add it to .env")
    else:
        st.subheader("Generating report...")
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(pct, msg):
            progress_bar.progress(pct)
            status_text.text(msg)

        start_time = time.time()
        sections = generate_all_sections(stats, context, report_depth, "groq", progress_callback=update_progress)
        total_latency = round(time.time() - start_time, 2)

        # Determine model used (from first section)
        model_used = ""
        for s in sections.values():
            model_used = s.get('model', '')
            break

        # Build content dict for PDF
        content_dict = {name: data['text'] for name, data in sections.items()}

        # Generate PDF
        pdf_bytes = generate_pdf_report(stats, context, content_dict, report_depth, provider_name="groq")

        st.success(f"Done! Total: {total_latency}s")

        # Download button — filename includes depth so different versions
        # of the same location's report don't overwrite each other.
        safe_name = location_name.replace(' ', '_').replace(',', '')
        safe_depth = report_depth.replace(' ', '_')
        pdf_filename = f"CHAT_Report_{safe_name}_{safe_depth}.pdf"
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf"
        )

        # Show sections in expanders
        for section_name, section_data in sections.items():
            with st.expander(section_name.replace('_', ' ').title()):
                st.write(section_data['text'])
