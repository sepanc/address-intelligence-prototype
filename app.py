import streamlit as st
import pandas as pd
from pipeline import run_pipeline

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Address Intelligence | Precisely",
    page_icon="📍",
    layout="wide"
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .narrative-box {
        background: #f8f9fa;
        border-left: 4px solid #dee2e6;
        padding: 1rem 1.2rem;
        border-radius: 4px;
        font-size: 0.95rem;
        line-height: 1.7;
        min-height: 100px;
    }
    .step-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6c757d;
        margin-bottom: 0.3rem;
    }
    .step-1 { border-left-color: #adb5bd; }
    .step-2 { border-left-color: #f4a261; background: #fff9f5; }
    .step-3 { border-left-color: #2a9d8f; background: #f0faf9; }
    .step-4 { border-left-color: #0066cc; background: #f0f6ff; }
    .correction-pill {
        display: inline-block;
        background: #d4edda;
        color: #155724;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin-top: 4px;
    }
    .no-correction-pill {
        display: inline-block;
        background: #e9ecef;
        color: #495057;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

PRECISION_LABELS = {
    "ADDRESS_POINT": "Building Level",
    "STREET"       : "Street Level",
    "POSTAL"       : "ZIP Code Level",
    "CITY"         : "City Level"
}

# ── Header ─────────────────────────────────────────────────────────────────
st.title("📍 Address Intelligence Prototype")
st.caption("Powered by Precisely APIs · Each step adds intelligence · See premium leakage close in real time")

tab1, tab2 = st.tabs(["Single Address", "Batch Upload"])

# ══════════════════════════════════════════════════════════════════════════
# TAB 1 — Single Address
# ══════════════════════════════════════════════════════════════════════════
with tab1:
    col_input, col_type = st.columns([4, 1])
    with col_input:
        address = st.text_input(
            "Enter a raw policyholder address",
            placeholder="e.g. 885 AVENUE OF THE AMERICASS Drv APT 38D, NEW YORK NY 10001"
        )
    with col_type:
        proptype = st.selectbox("Property Type", ["R", "B", "M", "X"])

    run = st.button("Run Pipeline", type="primary", disabled=not address)

    if run and address:
        with st.spinner("Running pipeline — verify → geocode → enrich → assess..."):
            result = run_pipeline(address, proptype)

        if "error" in result:
            st.error(f"Pipeline error: {result['error']}")
            st.stop()

        v = result["verify"]
        g = result["geo"]
        e = result["enrichment"]

        # ── Step 1 — Raw Input ─────────────────────────────────────────────
        st.divider()
        st.markdown("### Step 1 — Raw Input")
        st.markdown(f"**Submitted:** `{address}`")
        st.markdown(f'<p class="step-label">Underwriter Assessment — Address Only</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="narrative-box step-1">{result.get("narrative_raw","—")}</div>', unsafe_allow_html=True)

        # ── Step 2 — Verification ──────────────────────────────────────────
        st.divider()
        st.markdown("### Step 2 — Address Verification")
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("Verified Address", v.get("verified_address", "—"))
        v2.metric("City / State / ZIP", f"{v.get('verified_city')}, {v.get('verified_state')} {v.get('verified_zip')}")
        v3.metric("Match Score", v.get("score", "—"))
        corrected = v.get("corrected", False)
        badge = "correction-pill" if corrected else "no-correction-pill"
        label = "✅ Corrected" if corrected else "No Changes"
        v4.markdown(f'<p class="step-label">Correction</p><span class="{badge}">{label}</span>', unsafe_allow_html=True)

        st.markdown(f'<p class="step-label">Underwriter Assessment — After Verification</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="narrative-box step-2">{result.get("narrative_verified","—")}</div>', unsafe_allow_html=True)

        # ── Step 3 — Geocoding ─────────────────────────────────────────────
        st.divider()
        st.markdown("### Step 3 — Geocoding")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Latitude", round(g.get("latitude", 0), 6))
        g2.metric("Longitude", round(g.get("longitude", 0), 6))
        g3.metric("Precision", PRECISION_LABELS.get(g.get("precision",""), g.get("precision","")))
        g4.metric("PreciselyID", g.get("pb_key", "—"))

        st.markdown(f'<p class="step-label">Underwriter Assessment — After Geocoding</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="narrative-box step-3">{result.get("narrative_geocoded","—")}</div>', unsafe_allow_html=True)

        # ── Step 4 — Enrichment ────────────────────────────────────────────
        st.divider()
        st.markdown("### Step 4 — Location Enrichment")
        e1, e2, e3, e4, e5 = st.columns(5)
        e1.metric("Flood Zone", e.get("enrich_flood_zone") or "—")
        e2.metric("Dist to 100yr Flood", f"{e.get('enrich_flood_dist_100yr') or '—'} ft")
        e3.metric("Fire Station", f"{e.get('enrich_fire_station_dist_mi') or '—'} mi")
        e4.metric("Neighborhood", e.get("enrich_segment") or "—")
        e5.metric("Avg Home Value", f"${float(e.get('enrich_avg_home_value') or 0):,.0f}" if e.get("enrich_avg_home_value") else "—")

        with st.expander("See all enrichment data"):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Flood**")
                st.write(f"Zone: {e.get('enrich_flood_zone','—')}")
                st.write(f"100yr distance: {e.get('enrich_flood_dist_100yr','—')} ft")
                st.write(f"500yr distance: {e.get('enrich_flood_dist_500yr','—')} ft")
                st.write(f"Elevation: {e.get('enrich_flood_elevation','—')} ft")
                st.markdown("**Property**")
                st.write(f"Building sqft: {e.get('enrich_building_area_sqft','—')}")
                st.write(f"Year built: {e.get('enrich_year_built','—')}")
            with col_b:
                st.markdown("**Fire**")
                st.write(f"Distance: {e.get('enrich_fire_station_dist_mi','—')} mi")
                st.write(f"Drive time (peak): {e.get('enrich_fire_drivetime_peak_min','—')} min")
                st.write(f"Drive time (night): {e.get('enrich_fire_drivetime_night_min','—')} min")
                st.markdown("**Demographics**")
                st.write(f"Segment: {e.get('enrich_segment','—')}")
                st.write(f"Income tier: {e.get('enrich_income_tier','—')}")
                st.write(f"Avg income: ${float(e.get('enrich_avg_income') or 0):,.0f}" if e.get('enrich_avg_income') else "Avg income: —")
                st.write(f"Avg rent: ${float(e.get('enrich_avg_rent') or 0):,.0f}" if e.get('enrich_avg_rent') else "Avg rent: —")

        st.markdown(f'<p class="step-label">Final Underwriter Assessment — Full Enrichment</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="narrative-box step-4">{result.get("narrative_enriched","—")}</div>', unsafe_allow_html=True)

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
                results  = []
                progress = st.progress(0)
                status   = st.empty()

                for i, row in df.iterrows():
                    addr = str(row["address"])
                    pt   = str(row.get("proptype", "R"))
                    status.text(f"Processing {i+1}/{len(df)}: {addr[:50]}...")

                    r = run_pipeline(addr, pt)
                    results.append({
                        "raw_address"       : addr,
                        "verified_address"  : r.get("verified_address", ""),
                        "corrected"         : r.get("verify", {}).get("corrected", False),
                        "match_score"       : r.get("verify", {}).get("score", ""),
                        "pb_key"            : r.get("geo", {}).get("pb_key", ""),
                        "flood_zone"        : r.get("enrichment", {}).get("enrich_flood_zone", ""),
                        "fire_dist_mi"      : r.get("enrichment", {}).get("enrich_fire_station_dist_mi", ""),
                        "neighborhood"      : r.get("enrichment", {}).get("enrich_segment", ""),
                        "avg_home_value"    : r.get("enrichment", {}).get("enrich_avg_home_value", ""),
                        "narrative_enriched": r.get("narrative_enriched", ""),
                    })
                    progress.progress((i + 1) / len(df))

                status.text("✅ Complete")
                results_df = pd.DataFrame(results)
                st.dataframe(results_df, use_container_width=True)

                csv = results_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label     = "Download Results CSV",
                    data      = csv,
                    file_name = "batch_scored.csv",
                    mime      = "text/csv"
                )