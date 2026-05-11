import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
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

SCORED_FILE = Path(__file__).parent / "data" / "synthetic_250_scored.csv"

st.title("📍 Address Intelligence Prototype")
st.caption("Powered by Precisely APIs · Each step adds intelligence · See premium leakage close in real time")

tab1, tab2, tab3 = st.tabs(["Single Address", "Portfolio Intelligence", "Batch Upload"])

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
        proptype = st.selectbox("Property Type", ["R", "B", "M", "X"], key="t1_proptype")

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

        st.divider()
        st.markdown("### Step 1 — Raw Input")
        st.markdown(f"**Submitted:** `{address}`")
        st.markdown('<p class="step-label">Underwriter Assessment — Address Only</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="narrative-box step-1">{result.get("narrative_raw","—")}</div>', unsafe_allow_html=True)

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
        st.markdown('<p class="step-label">Underwriter Assessment — After Verification</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="narrative-box step-2">{result.get("narrative_verified","—")}</div>', unsafe_allow_html=True)

        st.divider()
        st.markdown("### Step 3 — Geocoding")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Latitude", round(g.get("latitude", 0), 6))
        g2.metric("Longitude", round(g.get("longitude", 0), 6))
        g3.metric("Precision", PRECISION_LABELS.get(g.get("precision",""), g.get("precision","")))
        g4.metric("PreciselyID", g.get("pb_key", "—"))
        st.markdown('<p class="step-label">Underwriter Assessment — After Geocoding</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="narrative-box step-3">{result.get("narrative_geocoded","—")}</div>', unsafe_allow_html=True)

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

        st.markdown('<p class="step-label">Final Underwriter Assessment — Full Enrichment</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="narrative-box step-4">{result.get("narrative_enriched","—")}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 2 — Portfolio Intelligence
# ══════════════════════════════════════════════════════════════════════════
with tab2:
    if not SCORED_FILE.exists():
        st.warning("No scored dataset found. Run the notebook pipeline first.")
        st.stop()

    df = pd.read_csv(SCORED_FILE)
    df["mcp_verify_score"] = pd.to_numeric(df["mcp_verify_score"], errors="coerce").fillna(0)

    with st.expander("📌 Assumptions — Based on Public Industry Data"):
        st.markdown("""
| Assumption | Value | Source |
|---|---|---|
| Avg annual residential premium (NJ) | $1,400 | NJ DOI Rate Filings 2023 |
| Premium mispricing rate (bad address) | 8–12% | ISO Loss Cost Studies |
| Avg adjuster cost per misrouted claim | $500–$800 | NAIC Claims Handling Guidelines |
| NJ DOI fine per unverifiable location | Up to $5,000 | NJ DOI Administrative Code |
| Portfolio size (carrier) | 300,000 | Assignment brief |
| Bad data rate (observed in sample) | 22% | This dataset (55/250) |
| Precisely correction rate | 78% | This dataset (43/55) |
        """)

    st.subheader("Business Impact — Address Intelligence at Scale")
    st.caption("Extrapolated from 250-record sample to 300,000 policyholder portfolio")

    PORTFOLIO       = 300_000
    AVG_PREMIUM     = 1_400
    BAD_DATA_RATE   = 55 / 250
    CORRECTION_RATE = 43 / 55
    BLIND_SPOT_RATE = 12 / 250
    ADJUSTER_LOW    = 500
    ADJUSTER_HIGH   = 800
    DOI_FINE        = 5_000
    MISPRICING_LOW  = 0.08
    MISPRICING_HIGH = 0.12

    dirty_est       = int(PORTFOLIO * BAD_DATA_RATE)
    correctable     = int(dirty_est * CORRECTION_RATE)
    blind_spots_est = int(PORTFOLIO * BLIND_SPOT_RATE)

    # ── Extrapolation table ────────────────────────────────────────────────
    extrap_data = [
        {"Metric"                : "Total portfolio records",
         "Sample (250)"          : "250",
         "Rate"                  : "—",
         "Extrapolated (300,000)": f"{PORTFOLIO:,}"},
        {"Metric"                : "Records with bad address data",
         "Sample (250)"          : "55",
         "Rate"                  : f"{BAD_DATA_RATE*100:.0f}%",
         "Extrapolated (300,000)": f"{dirty_est:,}"},
        {"Metric"                : "Correctable by Precisely",
         "Sample (250)"          : "43",
         "Rate"                  : f"{CORRECTION_RATE*100:.0f}% of dirty",
         "Extrapolated (300,000)": f"{correctable:,}"},
        {"Metric"                : "Verification blind spots",
         "Sample (250)"          : "12",
         "Rate"                  : f"{BLIND_SPOT_RATE*100:.1f}%",
         "Extrapolated (300,000)": f"{blind_spots_est:,}"},
    ]
    st.dataframe(pd.DataFrame(extrap_data), width="stretch", hide_index=True)

    st.divider()
    st.markdown("### 1 — Premium Mispricing Risk")
    st.caption("Incorrect risk zone assignments due to bad addresses lead to underpriced or overpriced premiums.")
    mispricing_low  = int(dirty_est * AVG_PREMIUM * MISPRICING_LOW)
    mispricing_high = int(dirty_est * AVG_PREMIUM * MISPRICING_HIGH)
    recovered_low   = int(correctable * AVG_PREMIUM * MISPRICING_LOW)
    recovered_high  = int(correctable * AVG_PREMIUM * MISPRICING_HIGH)
    p1, p2, p3 = st.columns(3)
    p1.metric("Est. Records with Bad Addresses", f"{dirty_est:,}", f"{BAD_DATA_RATE*100:.0f}% of portfolio")
    p2.metric("Annual Premium at Risk", f"${mispricing_low/1e6:.1f}M – ${mispricing_high/1e6:.1f}M")
    p3.metric("Recoverable with Precisely", f"${recovered_low/1e6:.1f}M – ${recovered_high/1e6:.1f}M", f"{CORRECTION_RATE*100:.0f}% correction rate")

    st.divider()
    st.markdown("### 2 — Claims Routed to Wrong Service Territory")
    st.caption("Misverified addresses place policyholders in wrong adjuster territories, wasting time and money.")
    claims_rate  = 0.08
    misrouted    = int(dirty_est * claims_rate)
    routing_low  = int(misrouted * ADJUSTER_LOW)
    routing_high = int(misrouted * ADJUSTER_HIGH)
    c1, c2, c3 = st.columns(3)
    c1.metric("Est. Claims Misrouted Annually", f"{misrouted:,}", "8% claim rate on bad records")
    c2.metric("Wasted Adjuster Cost", f"${routing_low/1e6:.2f}M – ${routing_high/1e6:.2f}M")
    c3.metric("Avg Cost per Misrouted Claim", "$500 – $800")

    st.divider()
    st.markdown("### 3 — Compliance Exposure")
    st.caption("Records unverifiable to a physical location create regulatory exposure under NJ DOI requirements.")
    compliance_low  = int(blind_spots_est * DOI_FINE * 0.1)
    compliance_high = int(blind_spots_est * DOI_FINE * 0.3)
    co1, co2, co3 = st.columns(3)
    co1.metric("Est. Unverifiable Records", f"{blind_spots_est:,}", "Blind spots not caught by verification")
    co2.metric("Potential DOI Exposure", f"${compliance_low/1e6:.1f}M – ${compliance_high/1e6:.1f}M", "At 10–30% enforcement rate")
    co3.metric("Max Fine per Record", "$5,000", "NJ DOI Administrative Code")

    st.divider()
    st.markdown("### 4 — AI Underwriting Readiness")
    st.caption("Verification score distribution determines which records are ready for AI-driven underwriting.")
    score_bins = [100, 90, 80, 70, 50, 0]
    bin_labels = ["100 — Fully Ready", "90–99 — High Confidence", "80–89 — Moderate", "70–79 — Marginal", "50–69 — At Risk"]
    loadings   = [0.0, 0.02, 0.05, 0.10, 0.15]
    tier_counts = []
    for i in range(len(bin_labels)):
        lo, hi = score_bins[i+1], score_bins[i]
        count  = int((df["mcp_verify_score"] == 100).sum()) if hi == 100 else int(((df["mcp_verify_score"] >= lo) & (df["mcp_verify_score"] < hi)).sum())
        pct    = count / len(df)
        est    = int(pct * PORTFOLIO)
        lo_imp = int(est * AVG_PREMIUM * loadings[i] * 0.5)
        hi_imp = int(est * AVG_PREMIUM * loadings[i])
        tier_counts.append({
            "AI Readiness Tier"     : bin_labels[i],
            "Sample Count"          : count,
            "Est. Portfolio Records": f"{est:,}",
            "Premium Loading"       : f"+{loadings[i]*100:.0f}%",
            "Uncertainty Cost"      : f"${lo_imp/1e6:.1f}M – ${hi_imp/1e6:.1f}M" if loadings[i] > 0 else "None"
        })
    st.dataframe(pd.DataFrame(tier_counts), width="stretch", hide_index=True)
    fully_ready_pct = int((df["mcp_verify_score"] == 100).sum() / len(df) * 100)
    not_ready       = int(PORTFOLIO * (1 - (df["mcp_verify_score"] == 100).sum() / len(df)))
    st.markdown(f"**{fully_ready_pct}%** of records are fully AI-ready after Precisely verification. "
                f"**{not_ready:,}** records in a 300K portfolio would require premium loading or manual review without it.")

    st.divider()
    st.markdown("### Sample Underwriter Narratives")
    st.caption("Before (basic) vs After (enriched) — filter to explore the portfolio")

    f1, f2, f3 = st.columns(3)
    with f1:
        filter_dirty = st.selectbox("Record type", ["All", "Dirty only", "Clean only"], key="t2_dirty")
    with f2:
        cats = ["All"] + sorted(df["mutation_category"].dropna().unique().tolist()) if "mutation_category" in df.columns else ["All"]
        filter_cat = st.selectbox("Mutation category", cats, key="t2_cat")
    with f3:
        pts = ["All"] + sorted(df["PROPTYPE"].dropna().unique().tolist()) if "PROPTYPE" in df.columns else ["All"]
        filter_pt = st.selectbox("Property type", pts, key="t2_pt")

    filtered = df.copy()
    if filter_dirty == "Dirty only":
        filtered = filtered[filtered["is_dirty"] == True]
    elif filter_dirty == "Clean only":
        filtered = filtered[filtered["is_dirty"] == False]
    if filter_cat != "All" and "mutation_category" in filtered.columns:
        filtered = filtered[filtered["mutation_category"] == filter_cat]
    if filter_pt != "All" and "PROPTYPE" in filtered.columns:
        filtered = filtered[filtered["PROPTYPE"] == filter_pt]

    st.caption(f"Showing {min(50, len(filtered))} of {len(filtered)} records")

    if "mutation_category" in filtered.columns:
        chart_df           = filtered.copy()
        chart_df["category"] = chart_df.apply(lambda r: r["mutation_category"] if r["is_dirty"] else "clean", axis=1)
        cat_counts         = chart_df["category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Count"]
        color_map = {
            "clean"             : "#2a9d8f",
            "street_typo"       : "#e63946",
            "missing_unit"      : "#f4a261",
            "flood_zip_mismatch": "#e9c46a",
            "zip_city_mismatch" : "#e76f51",
            "unresolvable"      : "#9d0208",
        }
        fig = px.pie(cat_counts, names="Category", values="Count", color="Category",
                     color_discrete_map=color_map, title="Record Distribution by Category", height=400)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(showlegend=True, font_size=13)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander(f"📋 View narrative records ({min(50, len(filtered))} shown)"):
        narrative_cols = ["ADDRLINE1","CITY","ADMIN1","is_dirty","mutation_category","mcp_verify_score","basic_narrative","enhanced_narrative"]
        available      = [c for c in narrative_cols if c in filtered.columns]
        st.dataframe(filtered[available].head(50), width="stretch", hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# TAB 3 — Batch Upload
# ══════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Batch Address Processing")
    st.caption("Upload a CSV with an `address` column and optional `proptype` column.")

    uploaded = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded:
        df_batch = pd.read_csv(uploaded)
        st.write(f"**{len(df_batch)} records loaded**")
        st.dataframe(df_batch.head(5), width="stretch")

        if "address" not in df_batch.columns:
            st.error("CSV must have an `address` column.")
        else:
            if st.button("Run Batch Pipeline", type="primary"):
                results  = []
                progress = st.progress(0)
                status   = st.empty()

                for i, row in df_batch.iterrows():
                    addr = str(row["address"])
                    pt   = str(row.get("proptype", "R"))
                    status.text(f"Processing {i+1}/{len(df_batch)}: {addr[:50]}...")
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
                    progress.progress((i + 1) / len(df_batch))

                status.text("✅ Complete")
                results_df = pd.DataFrame(results)
                st.dataframe(results_df, width="stretch")

                csv = results_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label     = "Download Results CSV",
                    data      = csv,
                    file_name = "batch_scored.csv",
                    mime      = "text/csv"
                )