import re
import math
import json
import requests
from pathlib import Path
from typing import Optional

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# ── Config ─────────────────────────────────────────────────────────────────
MCP_BASE_URL = "http://127.0.0.1:8000/mcp"
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral:7b"

MCP_HEADERS  = {
    "Accept"      : "application/json, text/event-stream",
    "Content-Type": "application/json"
}

# ── MCP call helper ────────────────────────────────────────────────────────
def mcp_call(tool: str, arguments: dict, timeout: int = 15) -> dict:
    resp = requests.post(
        MCP_BASE_URL,
        headers=MCP_HEADERS,
        json={
            "jsonrpc": "2.0",
            "id"     : 1,
            "method" : "tools/call",
            "params" : {"name": tool, "arguments": arguments}
        },
        timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()["result"]["structuredContent"]

# ── Format helper ──────────────────────────────────────────────────────────
def fmt(val, sentinel=-999999.0):
    if val is None or (isinstance(val, float) and (math.isnan(val) or val == sentinel)):
        return "unavailable"
    return str(val)

# ── 1. Verify address ──────────────────────────────────────────────────────
def verify_address(address: str, country: str = "USA") -> dict:
    data = mcp_call("verify_address", {"address": address, "country": country})
    try:
        result  = data["responses"][0]["results"][0]
        addr    = result.get("address", {})
        score   = result.get("score", 0)

        out_street = addr.get("formattedStreetAddress", "").strip().upper()
        out_city   = addr.get("city", {}).get("longName", "").strip().upper()
        out_state  = addr.get("admin1", {}).get("shortName", "").strip().upper()
        out_zip    = addr.get("postalCode", "").strip()

        return {
            "status"          : "ok",
            "verified_address": addr.get("formattedStreetAddress", ""),
            "verified_city"   : addr.get("city", {}).get("longName", ""),
            "verified_state"  : addr.get("admin1", {}).get("shortName", ""),
            "verified_zip"    : addr.get("postalCode", ""),
            "score"           : score,
            "corrected"       : any([
                out_street != address.upper().split(",")[0].strip(),
                out_city   != address.upper().split(",")[1].strip() if "," in address else False,
            ])
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ── 2. Geocode ─────────────────────────────────────────────────────────────
def geocode_address(address: str, country: str = "USA") -> dict:
    data = mcp_call("geocode", {"address": address, "country": country})
    try:
        result  = data["responses"][0]["results"][0]
        coords  = result["location"]["feature"]["geometry"]["coordinates"]
        custom  = result.get("customFields", {})
        return {
            "status"   : "ok",
            "latitude" : coords[1],
            "longitude": coords[0],
            "score"    : result.get("score", 0),
            "pb_key"   : custom.get("PB_KEY", ""),
            "precision": result.get("location", {}).get("explanation", {}).get("type", "")
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ── 3. Enrich ──────────────────────────────────────────────────────────────
def enrich_address(address: str, country: str = "USA") -> dict:
    enrichment = {}

    # Flood risk
    try:
        data  = mcp_call("get_flood_risk_by_address", {"address": address, "country": country}, timeout=20)
        flood = data["data"]["getByAddress"]["addresses"]["data"][0]["floodRisk"]["data"][0]
        enrichment.update({
            "enrich_flood_zone"      : flood.get("floodZone", ""),
            "enrich_flood_dist_100yr": flood.get("year100FloodZoneDistanceFeet", ""),
            "enrich_flood_dist_500yr": flood.get("year500FloodZoneDistanceFeet", ""),
            "enrich_flood_elevation" : flood.get("addressLocationElevationFeet", ""),
        })
    except Exception:
        enrichment.update({
            "enrich_flood_zone": "", "enrich_flood_dist_100yr": "",
            "enrich_flood_dist_500yr": "", "enrich_flood_elevation": ""
        })

    # Fire risk
    try:
        data = mcp_call("get_property_fire_risk", {"address": address, "country": country}, timeout=20)
        fire = data["data"]["getByAddress"]["addresses"]["data"][0]["propertyFireRisk"]["data"][0]
        enrichment.update({
            "enrich_fire_station_dist_mi"    : fire.get("firestation1DriveDistanceMiles", ""),
            "enrich_fire_drivetime_peak_min" : fire.get("firestation1DrivetimePMPeakMinutes", ""),
            "enrich_fire_drivetime_night_min": fire.get("firestation1DrivetimeNightMinutes", ""),
        })
    except Exception:
        enrichment.update({
            "enrich_fire_station_dist_mi": "",
            "enrich_fire_drivetime_peak_min": "",
            "enrich_fire_drivetime_night_min": ""
        })

    # Property attributes
    try:
        data = mcp_call("get_property_attributes_by_address", {"address": address, "country": country}, timeout=20)
        prop = data["data"]["getByAddress"]["propertyAttributes"]["data"][0]
        enrichment.update({
            "enrich_building_area_sqft": prop.get("buildingSquareFootage", ""),
            "enrich_year_built"        : prop.get("yearBuilt", ""),
        })
    except Exception:
        enrichment.update({
            "enrich_building_area_sqft": "",
            "enrich_year_built"        : ""
        })

    # Demographics
    try:
        data  = mcp_call("get_demographics", {"address": address, "country": country}, timeout=20)
        addr_data = data["data"]["getByAddress"]["addresses"]["data"][0]
        psyte = addr_data["psyteGeodemographics"]["data"][0]
        gv    = addr_data["groundView"]["data"][0]
        enrichment.update({
            "enrich_segment"       : psyte.get("PSYTESegmentCode", {}).get("description", ""),
            "enrich_income_tier"   : psyte.get("householdIncomeVariable", {}).get("description", ""),
            "enrich_avg_income"    : gv.get("averageHouseholdIncome", ""),
            "enrich_avg_home_value": gv.get("averageHomeValue", ""),
            "enrich_avg_rent"      : gv.get("averageRent", ""),
        })
    except Exception:
        enrichment.update({
            "enrich_segment": "", "enrich_income_tier": "",
            "enrich_avg_income": "", "enrich_avg_home_value": "", "enrich_avg_rent": ""
        })

    return enrichment

# ── Narrative prompts ──────────────────────────────────────────────────────
PROMPT_RAW = """You are an insurance underwriting AI reviewing a raw policyholder-submitted address.

Raw address  : {raw_address}
Property type: {proptype}

Write 2-3 sentences on what you can assess from this raw input alone.
Be explicit about what risk factors you cannot determine and why that creates premium uncertainty.
Reply with ONLY the narrative text."""

PROMPT_VERIFIED = """You are an insurance underwriting AI. This address has been verified and standardized by Precisely.

Raw address     : {raw_address}
Verified address: {verified_address}
Corrections made: {corrections}
Property type   : {proptype}

Previous assessment was based on raw input only.
Write 2-3 sentences: what did verification change, and what risk insight did the correction unlock?
If corrections were made, explicitly state what premium mispricing the raw address would have caused.
Reply with ONLY the narrative text."""

PROMPT_GEOCODED = """You are an insurance underwriting AI. This address has been verified and geocoded to building level by Precisely.

Verified address: {verified_address}
Latitude        : {latitude}
Longitude       : {longitude}
Precision       : {precision}
PreciselyID     : {pb_key}
Property type   : {proptype}

Previous assessment was based on verified address only.
Write exactly 2-3 sentences. No bullet points. No numbered lists.
What does building-level geocoding add to the risk picture?
What can you now assess that the address alone could not support — CAT model placement, flood map matching, fire district routing?
Reply with ONLY the narrative text."""

PROMPT_ENRICHED = """You are an insurance underwriting AI delivering a final underwriting assessment.

Verified address : {verified_address}
Property type    : {proptype}
Flood zone       : {flood_zone}
Dist to 100yr    : {flood_dist_100yr} ft
Dist to 500yr    : {flood_dist_500yr} ft
Elevation        : {flood_elevation} ft
Building sqft    : {building_sqft}
Year built       : {year_built}
Fire station     : {fire_dist} mi
Fire drive peak  : {fire_peak} min
Fire drive night : {fire_night} min
Neighborhood     : {segment}
Income tier      : {income_tier}
Avg income       : {avg_income}
Avg home value   : {avg_home_value}
Avg rent         : {avg_rent}

Previous assessment was based on geocode only — no enrichment data.
Write 2-3 sentences: lead with the dominant risk factor the enrichment data revealed.
Explicitly state what premium adjustment the enrichment data justifies compared to what the raw address suggested.
Reply with ONLY the narrative text."""

# ── 4. Generate narratives ─────────────────────────────────────────────────
def llm(prompt: str, timeout: int = 60) -> str:
    resp = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=timeout
    )
    raw = resp.json().get("response", "").strip()
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

def generate_narratives(
    raw_address: str,
    proptype: str,
    verify: dict,
    geo: dict,
    enrichment: dict
) -> dict:
    verified_addr = f"{verify['verified_address']}, {verify['verified_city']}, {verify['verified_state']} {verify['verified_zip']}"

    # Build corrections summary
    corrections = "None detected" if not verify.get("corrected") else (
        f"Address standardized from '{raw_address}' to '{verified_addr}'"
    )

    precision_labels = {
        "ADDRESS_POINT": "Building Level",
        "STREET"       : "Street Level",
        "POSTAL"       : "ZIP Code Level",
        "CITY"         : "City Level"
    }
    precision = precision_labels.get(geo.get("precision", ""), geo.get("precision", ""))

    narrative_raw = llm(PROMPT_RAW.format(
        raw_address = raw_address,
        proptype    = proptype
    ))

    narrative_verified = llm(PROMPT_VERIFIED.format(
        raw_address      = raw_address,
        verified_address = verified_addr,
        corrections      = corrections,
        proptype         = proptype
    ))

    narrative_geocoded = llm(PROMPT_GEOCODED.format(
        verified_address = verified_addr,
        latitude         = geo.get("latitude", ""),
        longitude        = geo.get("longitude", ""),
        precision        = precision,
        pb_key           = geo.get("pb_key", ""),
        proptype         = proptype
    ))

    narrative_enriched = llm(PROMPT_ENRICHED.format(
        verified_address = verified_addr,
        proptype         = proptype,
        flood_zone       = fmt(enrichment.get("enrich_flood_zone")),
        flood_dist_100yr = fmt(enrichment.get("enrich_flood_dist_100yr")),
        flood_dist_500yr = fmt(enrichment.get("enrich_flood_dist_500yr")),
        flood_elevation  = fmt(enrichment.get("enrich_flood_elevation")),
        building_sqft    = fmt(enrichment.get("enrich_building_area_sqft")),
        year_built       = fmt(enrichment.get("enrich_year_built")),
        fire_dist        = fmt(enrichment.get("enrich_fire_station_dist_mi")),
        fire_peak        = fmt(enrichment.get("enrich_fire_drivetime_peak_min")),
        fire_night       = fmt(enrichment.get("enrich_fire_drivetime_night_min")),
        segment          = fmt(enrichment.get("enrich_segment")),
        income_tier      = fmt(enrichment.get("enrich_income_tier")),
        avg_income       = fmt(enrichment.get("enrich_avg_income")),
        avg_home_value   = fmt(enrichment.get("enrich_avg_home_value")),
        avg_rent         = fmt(enrichment.get("enrich_avg_rent"))
    ))

    return {
        "narrative_raw"     : narrative_raw,
        "narrative_verified": narrative_verified,
        "narrative_geocoded": narrative_geocoded,
        "narrative_enriched": narrative_enriched,
    }

# ── 5. Full pipeline ───────────────────────────────────────────────────────
def run_pipeline(raw_address: str, proptype: str = "R") -> dict:
    result = {"raw_address": raw_address, "proptype": proptype}

    verify = verify_address(raw_address)
    result["verify"] = verify
    if verify["status"] == "error":
        result["error"] = verify["error"]
        return result

    verified_addr = f"{verify['verified_address']}, {verify['verified_city']}, {verify['verified_state']} {verify['verified_zip']}"
    result["verified_address"] = verified_addr

    geo = geocode_address(verified_addr)
    result["geo"] = geo

    enrichment = enrich_address(verified_addr)
    result["enrichment"] = enrichment

    narratives = generate_narratives(raw_address, proptype, verify, geo, enrichment)
    result.update(narratives)

    return result