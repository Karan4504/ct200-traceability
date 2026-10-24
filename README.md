# CardioTrack CT-200 Document Hierarchy & QA Test Traceability Pipeline

A production-grade, regulatory-compliant backend pipeline and API for parsing, structuring, versioning, and generating QA test cases with automated staleness and impact detection for medical device technical documentation (CardioTrack CT-200 Home Blood Pressure Monitor).

Developed for the **Tri9T AI Engineering Internship Assignment**.

---

## 🌟 Key Highlights

- **Pure-Python Typography & OCR Pipeline**: Parses real engineering PDFs, identifying titles, headings, levels, tables, lists, and hierarchical parent-child relationships.
- **Robust Irregularity Handling**:
  - Duplicate section titles (`4.2 Error Codes` vs `7.1 Error Codes`) mapped to distinct canonical nodes and parents.
  - Out-of-order numbering (`3.4 Auto Shutoff` before `3.3 Result Display`) parented correctly preserving document order.
  - Skipped hierarchy levels (`2.1.1.1` skipping `2.1.1` and attaching to `2.1`).
  - Distinguishes body numbered lists (1–5 in section 3.3) from section headings via typography weight detection.
  - Reconstructs multi-line table cells (Table 2.1 Parameter/Value, Table 4.2 Error Codes) into structured Markdown.
  - Normalizes inter-page continuations and ligatures (`fi`, `fl`, non-breaking hyphens) to prevent false-positive hash mismatches across pagination shifts.
- **Multi-Version Tree & Node Matching**: Re-ingests modified manuals (`ct200_manual_v2.pdf`) as new versions without destroying v1. Detects `UNCHANGED`, `MODIFIED`, and `ADDED` sections (such as `5.3 Data Export`) with line-level diffs.
- **Version-Pinned Selections**: Freezes node snapshots, text, and SHA-256 hashes at creation time.
- **LLM-Powered QA Test Generation**: Generates 3–5 concrete, executable QA test cases with Pydantic structured output validation, self-healing JSON repair, retry backoff, and a deterministic fallback engine.
- **Auditable Duplicate Selection Policy**: Caches results for identical selections to guarantee reproducibility and prevent token waste, with an explicit `force_regenerate=True` override.
- **Live Staleness & Impact Detection**: Evaluates whether previously generated test cases still reflect the current manual, categorizing numerical threshold changes (`CRITICAL_THRESHOLD_CHANGE`) vs wording modifications.
- **Complete Test Suite**: 19 automated tests covering irregularities, versioning, selections, LLM schemas, staleness, and API lifecycle.

---

## 🏗️ Architecture & Tech Stack

- **Backend Framework**: FastAPI & Uvicorn (RESTful API with OpenAPI docs)
- **Data Validation & Schemas**: Pydantic v1
- **Relational Tree & Version Store**: SQLite + SQLAlchemy 2.0
- **Document / Generation Store**: Dedicated NoSQL JSON document store (`nosql_store/`) with MongoDB driver compatibility
- **PDF Extraction**: Pure-Python `pypdf` visitor pipeline (extracting font sizes, font weights, coordinates, bounding boxes, text spans)
- **Testing**: Pytest

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Clone and Install Dependencies
```bash
git clone <repo-url>
cd ct200-traceability

# Create and activate virtual environment (optional but recommended)
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install required dependencies
python -m pip install -r requirements.txt
```

### 3. Environment Variables (Optional)
The system runs out of the box with zero configuration using the built-in deterministic QA generator. If you wish to connect real cloud LLMs:
```bash
# In .env or shell:
export LLM_PROVIDER=gemini        # 'gemini', 'groq', 'openai', or 'mock' (default)
export LLM_API_KEY=your_key_here
export LLM_MODEL=gemini-1.5-flash
export MAX_LLM_RETRIES=3
```

---

## 🧪 Running the Test Suite

Execute the comprehensive automated test suite:
```bash
python -m pytest -v
```

This verifies:
1. `tests/test_irregularities.py` — Duplicate headings (4.2 vs 7.1), out-of-order numbering (3.4 before 3.3), level jump (2.1.1.1), body numbered lists, table extraction, and cross-page text continuity.
2. `tests/test_versioning.py` — Logical node matching, diff computation, change flagging (MODIFIED/ADDED/UNCHANGED).
3. `tests/test_selections.py` — Version-pinned snapshots surviving subsequent re-ingestion.
4. `tests/test_llm_generation.py` — Pydantic schema validation, JSON repair, fallback.
5. `tests/test_staleness.py` — Staleness detection and semantic impact classification.
6. `tests/test_api_e2e.py` — Complete REST API lifecycle test.

---

## 🎬 Running the End-to-End Demo Script

Run the automated walkthrough showing the entire v1 → v2 re-ingestion and staleness detection lifecycle:
```bash
python demo_flow.py
```

---

## 🌐 Running the FastAPI Server

Launch the API server locally:
```bash
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger UI documentation is available at:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 🔄 How to Trigger the v1 → v2 Re-Ingestion Flow

### Step 1: Ingest Version 1
```bash
curl -X POST "http://127.0.0.1:8000/api/ingest" \
     -H "Content-Type: application/json" \
     -d '{"version": "v1", "pdf_path": "data/ct200_manual.pdf"}'
```

### Step 2: Create a Pinned Selection against v1
```bash
curl -X POST "http://127.0.0.1:8000/api/selections" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Overpressure Subsystem",
       "node_ids": ["v1_sec_4_1", "v1_sec_4_2"],
       "description": "Emergency deflation verification"
     }'
```
*Note the returned `id` (e.g., `sel_d34684c14867`).*

### Step 3: Generate QA Test Cases
```bash
curl -X POST "http://127.0.0.1:8000/api/generate" \
     -H "Content-Type: application/json" \
     -d '{"selection_id": "sel_d34684c14867", "force_regenerate": false}'
```
*Note the returned `generation_id` (e.g., `gen_dfec5990e8c8`). In v1, this generation is `FRESH` (auto-deflate is 2.0 seconds).*

### Step 4: Re-Ingest Version 2 (The Modified Manual)
```bash
curl -X POST "http://127.0.0.1:8000/api/ingest" \
     -H "Content-Type: application/json" \
     -d '{"version": "v2", "pdf_path": "data/ct200_manual_v2.pdf"}'
```
*Version 1 is preserved intact. Version 2 is ingested as a new version.*

### Step 5: Check Node Diff for Section 4.2
```bash
curl -X GET "http://127.0.0.1:8000/api/nodes/v1_sec_4_2/diff"
```
*Returns line-level diff showing E3 auto-deflate time changed from 2 seconds to 1.5 seconds and new error code E6 added.*

### Step 6: Query Generated Test Cases for Live Staleness
```bash
curl -X GET "http://127.0.0.1:8000/api/test-cases/gen_dfec5990e8c8"
```
*Response shows:*
```json
{
  "staleness_evaluation": {
    "is_stale": true,
    "staleness_status": "STALE",
    "pinned_version": "v1",
    "latest_version": "v2",
    "stale_nodes_count": 1,
    "stale_nodes": [
      {
        "logical_id": "sec_4_2",
        "heading": "4.2 Error Codes",
        "status": "STALE",
        "impact": "CRITICAL_THRESHOLD_CHANGE",
        "diff_summary": "Modified 2 line(s) into 3 line(s)."
      }
    ],
    "impact_summary": "1 of 2 referenced section(s) have changed since test cases were generated. WARNING: Numerical/threshold changes detected in '4.2 Error Codes': Modified 2 line(s) into 3 line(s)."
  }
}
```

---

## 📂 Project Structure

```
ct200-traceability/
├── data/
│   ├── ct200_manual.pdf                 # Original CT-200 technical manual (v1)
│   ├── ct200_manual_v2.pdf              # Revised manual with safety & sync changes (v2)
│   └── IMPORTANT_ASSIGNMENT_UPDATE.txt  # Guidance notes
├── src/
│   ├── config.py                        # Centralized settings and paths
│   ├── parser/
│   │   ├── models.py                    # ParsedNode & DocumentTree models
│   │   ├── pdf_extractor.py             # Coordinate & typography-aware PDF extractor
│   │   └── hierarchy_builder.py         # Tree builder handling all 6 document irregularities
│   ├── database/
│   │   ├── models.py                    # SQLAlchemy relational models
│   │   ├── connection.py                # SQLite engine & session setup
│   │   └── nosql_store.py               # NoSQL JSON document store for test generations
│   ├── versioning/
│   │   ├── diff_summary.py              # Unified and token-level diff engine
│   │   └── matcher.py                   # Canonical logical node matcher across versions
│   ├── llm/
│   │   ├── prompt.py                    # Medical device QA prompt templates
│   │   └── generator.py                 # Pydantic schema validation, JSON repair & retry
│   ├── staleness/
│   │   └── detector.py                  # Live staleness & semantic impact detection
│   └── api/
│       ├── main.py                      # FastAPI application
│       ├── schemas.py                   # Pydantic API schemas
│       └── routes/                      # Route handlers (ingest, browse, selection, generate, test_cases)
├── tests/
│   ├── test_irregularities.py           # 6 unit tests targeting specific PDF irregularities
│   ├── test_versioning.py               # Unit tests for node matching & change flagging
│   ├── test_selections.py               # Unit tests for version pinning
│   ├── test_llm_generation.py           # Unit tests for schema validation & repair
│   ├── test_staleness.py                # Unit tests for staleness & impact detection
│   └── test_api_e2e.py                  # End-to-end API lifecycle test
├── demo_flow.py                         # Standalone end-to-end demo script
├── requirements.txt                     # Dependencies
├── APPROACH.md                          # Comprehensive technical design doc & Decision Log
└── README.md                            # Documentation
```
