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

# ── 4. Generate narratives ─────────────────────────────────────────────────
def generate_narratives(verified_address: str, proptype: str, enrichment: dict) -> dict:

    basic_prompt = f"""You are an insurance underwriting AI. Write a 2-3 sentence underwriting assessment for this property based only on the verified address and property type.

Address      : {verified_address}
Property type: {proptype}

Be specific about what you can and cannot determine from the address alone.
Reply with ONLY the narrative text, no JSON, no labels."""

    enhanced_prompt = f"""You are an insurance underwriting AI. Write a 2-3 sentence underwriting assessment for this property using the verified address and full location intelligence data.

Address          : {verified_address}
Property type    : {proptype}
Flood zone       : {fmt(enrichment.get('enrich_flood_zone'))}
Dist to 100yr    : {fmt(enrichment.get('enrich_flood_dist_100yr'))} ft
Dist to 500yr    : {fmt(enrichment.get('enrich_flood_dist_500yr'))} ft
Elevation        : {fmt(enrichment.get('enrich_flood_elevation'))} ft
Building type    : {fmt(enrichment.get('enrich_building_type'))}
Building sqft    : {fmt(enrichment.get('enrich_building_area_sqft'))}
Fire station     : {fmt(enrichment.get('enrich_fire_station_dist_mi'))} mi
Fire drive peak  : {fmt(enrichment.get('enrich_fire_drivetime_peak_min'))} min
Fire drive night : {fmt(enrichment.get('enrich_fire_drivetime_night_min'))} min
Neighborhood     : {fmt(enrichment.get('enrich_segment'))}
Income tier      : {fmt(enrichment.get('enrich_income_tier'))}
Avg income       : {fmt(enrichment.get('enrich_avg_income'))}
Avg home value   : {fmt(enrichment.get('enrich_avg_home_value'))}
Avg rent         : {fmt(enrichment.get('enrich_avg_rent'))}

Lead with the dominant risk factor. Be specific about what the enrichment data reveals.
Reply with ONLY the narrative text, no JSON, no labels."""

    def llm(prompt):
        resp = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60
        )
        raw = resp.json().get("response", "").strip()
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    return {
        "basic_narrative"   : llm(basic_prompt),
        "enhanced_narrative": llm(enhanced_prompt)
    }

# ── 5. Full pipeline (single address) ─────────────────────────────────────
def run_pipeline(raw_address: str, proptype: str = "R") -> dict:
    result = {"raw_address": raw_address, "proptype": proptype}

    # Verify
    verify = verify_address(raw_address)
    result["verify"] = verify

    if verify["status"] == "error":
        result["error"] = verify["error"]
        return result

    verified_addr = f"{verify['verified_address']}, {verify['verified_city']}, {verify['verified_state']} {verify['verified_zip']}"
    result["verified_address"] = verified_addr

    # Geocode
    geo = geocode_address(verified_addr)
    result["geo"] = geo

    # Enrich
    enrichment = enrich_address(verified_addr)
    result["enrichment"] = enrichment

    # Narratives
    narratives = generate_narratives(verified_addr, proptype, enrichment)
    result.update(narratives)

    return result