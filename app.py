import streamlit as st
import pandas as pd
import io
from pipeline import run_pipeline

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Address Intelligence | Precisely",
    page_icon="📍",
    layout="wide"
)

# ── Styles ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .narrative-box {
        background: #f8f9fa;
        border-left: 4px solid #dee2e6;
        padding: 1rem 1.2rem;
        border-radius: 4px;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .narrative-enhanced {
        border-left-color: #0066cc;
        background: #f0f6ff;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .corrected-badge {
        background: #d4edda;
        color: #155724;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────
st.title("📍 Address Intelligence Prototype")
st.caption("Powered by Precisely APIs + Local LLM")

# ── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Single Address", "Batch Upload"])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — Single Address
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Single Address Analysis")
    st.caption("Enter a raw address — the pipeline will verify, geocode, enrich, and generate underwriting narratives.")

    col_input, col_type = st.columns([4, 1])
    with col_input:
        address = st.text_input(
            "Address",
            placeholder="e.g. 885 AVENUE OF THE AMERICASS Drv APT 38D, NEW YORK NY 10001",
            label_visibility="collapsed"
        )
    with col_type:
        proptype = st.selectbox("Property Type", ["R", "B", "M", "X"], label_visibility="collapsed")

    run = st.button("Run Pipeline", type="primary", disabled=not address)

    if run and address:
        with st.spinner("Running Precisely pipeline..."):
            result = run_pipeline(address, proptype)

        if "error" in result:
            st.error(f"Pipeline error: {result['error']}")
        else:
            # ── Verification row ───────────────────────────────────────────
            st.divider()
            st.markdown("#### Step 1 — Address Verification")
            v = result["verify"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Verified Address", v.get("verified_address", "—"))
            c2.metric("City / State / ZIP", f"{v.get('verified_city')}, {v.get('verified_state')} {v.get('verified_zip')}")
            c3.metric("Match Score", v.get("score", "—"))
            c4.metric("Corrected", "✅ Yes" if v.get("corrected") else "No")

            # ── Geocode row ────────────────────────────────────────────────
            st.markdown("#### Step 2 — Geocoding")
            g = result["geo"]
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Latitude", round(g.get("latitude", 0), 6))
            g2.metric("Longitude", round(g.get("longitude", 0), 6))
            g3.metric("Precision", g.get("precision", "—"))
            g4.metric("PreciselyID", g.get("pb_key", "—"))

            # ── Enrichment row ─────────────────────────────────────────────
            st.markdown("#### Step 3 — Location Enrichment")
            e = result["enrichment"]
            e1, e2, e3, e4, e5 = st.columns(5)
            e1.metric("Flood Zone", e.get("enrich_flood_zone") or "—")
            e2.metric("Dist to 100yr Flood", f"{e.get('enrich_flood_dist_100yr') or '—'} ft")
            e3.metric("Fire Station", f"{e.get('enrich_fire_station_dist_mi') or '—'} mi")
            e4.metric("Neighborhood", e.get("enrich_segment") or "—")
            e5.metric("Avg Home Value", f"${float(e.get('enrich_avg_home_value') or 0):,.0f}" if e.get("enrich_avg_home_value") else "—")

            # ── Narratives ─────────────────────────────────────────────────
            st.markdown("#### Step 4 — Underwriter Assessment")
            n1, n2 = st.columns(2)

            with n1:
                st.markdown("**🔍 Basic — Address Only**")
                st.markdown(
                    f'<div class="narrative-box">{result.get("basic_narrative", "—")}</div>',
                    unsafe_allow_html=True
                )

            with n2:
                st.markdown("**⚡ Enhanced — Precisely Enriched**")
                st.markdown(
                    f'<div class="narrative-box narrative-enhanced">{result.get("enhanced_narrative", "—")}</div>',
                    unsafe_allow_html=True
                )

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — Batch Upload
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Batch Address Processing")
    st.caption("Upload a CSV with an `address` column and optional `proptype` column.")

    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded:
        df = pd.read_csv(uploaded)
        st.write(f"**{len(df)} records loaded**")
        st.dataframe(df.head(5), use_container_width=True)

        if "address" not in df.columns:
            st.error("CSV must have an `address` column.")
        else:
            if st.button("Run Batch Pipeline", type="primary"):
                results = []
                progress = st.progress(0)
                status   = st.empty()

                for i, row in df.iterrows():
                    addr = str(row["address"])
                    pt   = str(row.get("proptype", "R"))
                    status.text(f"Processing {i+1}/{len(df)}: {addr[:50]}...")

                    r = run_pipeline(addr, pt)
                    results.append({
                        "raw_address"      : addr,
                        "verified_address" : r.get("verified_address", ""),
                        "corrected"        : r.get("verify", {}).get("corrected", False),
                        "match_score"      : r.get("verify", {}).get("score", ""),
                        "pb_key"           : r.get("geo", {}).get("pb_key", ""),
                        "flood_zone"       : r.get("enrichment", {}).get("enrich_flood_zone", ""),
                        "fire_dist_mi"     : r.get("enrichment", {}).get("enrich_fire_station_dist_mi", ""),
                        "neighborhood"     : r.get("enrichment", {}).get("enrich_segment", ""),
                        "avg_home_value"   : r.get("enrichment", {}).get("enrich_avg_home_value", ""),
                        "basic_narrative"  : r.get("basic_narrative", ""),
                        "enhanced_narrative": r.get("enhanced_narrative", ""),
                    })
                    progress.progress((i + 1) / len(df))

                status.text("✅ Complete")
                results_df = pd.DataFrame(results)
                st.dataframe(results_df, use_container_width=True)

                # Download
                csv = results_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download Results CSV",
                    data=csv,
                    file_name="batch_scored.csv",
                    mime="text/csv"
                )