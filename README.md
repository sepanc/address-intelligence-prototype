# Address Intelligence Prototype
### Powered by Precisely Data Integrity Suite APIs + Local LLM (Mistral 7b)

A end-to-end prototype demonstrating how poor-quality address data creates measurable business risk for insurance carriers — and how Precisely's APIs combined with a local AI layer transforms it into trusted, decision-ready data.

> **Business context:** A mid-sized national insurance carrier with 300,000+ policyholder records. Messy address data causes incorrect risk zone assignments, misrouted claims, compliance exposure, and blocks AI-driven underwriting automation.

---

## What This Prototype Builds

| Layer | What it does |
|---|---|
| **Synthetic dataset** | 250 records seeded from real Precisely-verified addresses, with 55 intentionally mutated across 5 error dimensions |
| **Address verification** | REST API + MCP pipeline — standardizes, corrects, and scores each address |
| **Geocoding** | Building-level lat/long + PreciselyID via MCP — 100% coverage, ADDRESS_POINT precision |
| **Location enrichment** | Flood risk, fire station proximity, property attributes, neighborhood demographics |
| **LLM scoring** | Two Mistral-generated narratives per record — Basic (address only) vs Enhanced (full enrichment) |
| **Streamlit app** | Live demo UI — single address pipeline + portfolio intelligence dashboard |

---

## Project Structure

```
address-intelligence-prototype/
├── data/
│   ├── rawdata.csv                      # Seed: 250 Precisely-verified records
│   ├── synthetic_250_with_mutations.csv # After mutation injection
│   ├── synthetic_250_restapi.csv        # After REST verification + geocode
│   ├── synthetic_250_mcp.csv            # After MCP verification + geocode
│   ├── synthetic_250_enriched.csv       # After flood, fire, demographics enrichment
│   └── synthetic_250_scored.csv        # Final: basic + enhanced LLM narratives
│
├── notebooks/
│   └── pipeline.ipynb                  # Full pipeline notebook (Cells 0–13)
│
├── pipeline.py                         # Shared pipeline module (used by app + notebook)
├── app.py                              # Streamlit demo application
├── .env                                # API credentials (not committed)
├── .env.template                       # Credential placeholders
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- [Ollama](https://ollama.com/) installed and running locally
- Precisely API free trial credentials from [developer.precisely.com](https://developer.precisely.com)
- Precisely MCP server running locally at `http://127.0.0.1:8000`

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/sepanc/address-intelligence-prototype.git
cd address-intelligence-prototype
```

**2. Create virtual environment and install dependencies**
```bash
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

**3. Configure environment variables**
```bash
cp .env.template .env
```

`.env` structure:
```
PRECISELY_API_KEY=your_api_key_here
PRECISELY_API_SECRET=your_api_secret_here
```

**4. Pull the Ollama model**
```bash
ollama pull mistral:7b
```

**5. Start the Precisely MCP server**

Follow setup instructions in the Precisely MCP server repo. The server must be running at `http://127.0.0.1:8000` before running the notebook or Streamlit app.

---

## Running the Notebook

Open `notebooks/pipeline.ipynb` in VS Code and run cells in order:

| Cell | Description |
|---|---|
| Cell 0 | Install dependencies via pip |
| Cell 1 | Config — paths, API credentials, Ollama model, mutation budget |
| Cell 2 | Load and inspect seed data — schema validation, PROPTYPE distribution |
| Cell 3 | Mutation target selection — deterministic selection of 55 dirty records |
| Cell 4 | Mutation functions — street typo, missing unit, flood ZIP mismatch, ZIP/city mismatch, unresolvable |
| Cell 5 | Apply mutations + Mistral LLM annotation — `llm_outcome_review` per dirty record |
| Cell 6 | Rebuild FORMATTEDADDRESS and ADDRLINE1 from mutated fields |
| Cell 7 | Export `synthetic_250_with_mutations.csv` |
| Cell 8 | Precisely OAuth2 token manager — auto-refresh |
| Cell 9 | REST address verification pipeline |
| Cell 9a | MCP address verification + Mistral LLM correction review |
| Cell 10 | REST geocoding (baseline) |
| Cell 10a | MCP geocoding — building-level precision, PreciselyID |
| Cell 10b | Export `synthetic_250_mcp.csv` |
| Cell 11 | Before/after comparison report — match rates, standardization, coordinate coverage, blind spots |
| Cell 12 | Location enrichment — flood risk, fire proximity, property attributes, demographics |
| Cell 13 | LLM narrative generation — Basic vs Enhanced underwriter assessment per record |

---

## Running the Streamlit App

```bash
streamlit run app.py
```

The app has three tabs:

| Tab | Description |
|---|---|
| **Single Address** | Enter a raw address → live pipeline → 4-step progressive narrative (raw → verified → geocoded → enriched) |
| **Portfolio Intelligence** | Business impact dashboard — extrapolated ROI from 250-record sample to 300K portfolio, AI readiness tiers, narrative explorer |
| **Batch Upload** | Upload a CSV with an `address` column → full pipeline → download scored output |

---

## Key Findings from the Prototype

| Metric | Value |
|---|---|
| Bad data rate (observed) | 22% (55/250 records) |
| MCP correction rate | 78% of dirty records corrected |
| Geocode coverage | 100% (250/250) |
| ADDRESS_POINT precision | 90.8% (227/250) |
| PreciselyID assigned | 90.8% (227/250) |
| Verification blind spots | 12 records (missing unit — slips through verification) |

---

## Mutation Categories

| Category | Records | Description |
|---|---|---|
| `flood_zip_mismatch` | 15 | ZIP swapped to inland code — moves property out of flood zone |
| `missing_unit` | 12 | Unit number dropped — unverifiable to specific occupancy |
| `street_typo` | 10 | Character-level noise in street name |
| `zip_city_mismatch` | 13 | Valid ZIP/city pair but wrong combination |
| `unresolvable` | 5 | Address number blanked, street vowels stripped |

---

## .env Template

```
PRECISELY_API_KEY=your_api_key_here
PRECISELY_API_SECRET=your_api_secret_here
```

> **Note on API credits:** The Precisely free trial includes 2,500 credits valid for 30 days. The full 250-record pipeline (verify + geocode + enrich) consumes approximately 750–1,000 credits. Plan usage before running the full dataset.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.12 | Pipeline and notebook |
| Precisely Data Integrity Suite APIs | Address verification, geocoding |
| Precisely MCP Server | Local MCP bridge for enrichment tools |
| Ollama + Mistral 7b | Local LLM for mutation annotation and risk narratives |
| Streamlit | Demo UI |
| Plotly | Portfolio intelligence charts |
| python-pptx | Slide deck generation |
| pandas | Data processing |

---

## Deliverables

- ✅ `notebooks/pipeline.ipynb` — commented, runnable end-to-end pipeline
- ✅ `data/synthetic_250_scored.csv` — before/after data with verification, geocode, enrichment, and LLM narratives
- ✅ `app.py` — Streamlit demo with single address + portfolio intelligence + batch upload
- ✅ `address_intelligence_deck.pptx` — 3-slide executive deck
- ✅ Business impact summary — one-pager in pdf format

---

## License

MIT