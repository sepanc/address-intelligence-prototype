# Address Intelligence Prototype
Powered by Precisely APIs + Ollama (Mistral 7b)

A pipeline that validates, geocodes, and enriches synthetic policyholder address data — demonstrating how poor-quality address data creates measurable business risk and how Precisely's Data Integrity Suite transforms it into trusted, decision-ready data.

---

## Project Structure

```
address-intelligence-prototype/
│
├── data/
│   ├── sample_before.csv
│   └── sample_after.csv
│
├── .env.template                # API key placeholders
├── .gitignore
└── requirements.txt
```

---

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running locally with `mistral:7b` pulled
- Precisely API free trial credentials from [developer.precisely.com](https://developer.precisely.com)

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/YOUR_USERNAME/address-intelligence-prototype.git
cd address-intelligence-prototype
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Copy `.env.template` to `.env` and fill in your credentials:
```bash
cp .env.template .env
```

`.env` structure:
```
PRECISELY_BASE_URL=https://api.precisely.com
PRECISELY_API_KEY=your_api_key_here
PRECISELY_API_SECRET=your_api_secret_here
```

**5. Pull the Mistral model via Ollama**
```bash
ollama pull mistral:7b
```

---

## Running the Notebook

Open `notebooks/preciselydemo.ipynb` in VS Code or Jupyter and run cells in order:

| Cell | Description |
|------|-------------|
| Cell 0 | **Fake Dataset Generation + Call API** — Shows the before and after of the API cleanup. Generates 20 synthetic records, validates via Precisely, exports 10-row sample CSVs |
| Cell 1–3 | Generates full 250-record synthetic dataset with controlled mutations |
| Cell 4–9 | Address verification and standardization pipeline |
| Cell 10–11 | Geocoding + PreciselyID assignment |
| Cell 12+ | Location enrichment and AI risk narrative layer |

> **Note on API credits:** The free trial includes 2,500 credits. Cell 0 consumes ~20 credits. The full 250-record pipeline consumes ~250–500 credits depending on enrichment calls. Run Cell 0 first to verify your credentials before running the full pipeline.

---

## Sample Output

`data/sample_before.csv` — raw input, no PBKEY, contains dirty records

`data/sample_after.csv` — validated output, PBKEY populated for verified records, corrections tracked per field