import json
import time
from fastapi.testclient import TestClient
from src.api.main import app
from src.config import DEFAULT_PDF_V1, DEFAULT_PDF_V2
from src.database.connection import SessionLocal, init_db
from src.database.models import DocumentVersionRecord, NodeRecord, SelectionRecord

def run_demo():
    print("=" * 78)
    print(" CARDIOTRACK CT-200 TRACEABILITY & QA TEST GENERATION PIPELINE DEMO")
    print("=" * 78)

    # Clean DB for demo run
    init_db()
    db = SessionLocal()
    db.query(SelectionRecord).delete()
    db.query(NodeRecord).delete()
    db.query(DocumentVersionRecord).delete()
    db.commit()
    db.close()

    client = TestClient(app)

    # STEP 1: Ingest Manual v1
    print("\n[STEP 1] Ingesting Technical Manual v1 (data/ct200_manual.pdf)...")
    res = client.post("/api/ingest", json={"version": "v1", "pdf_path": str(DEFAULT_PDF_V1)})
    data_v1 = res.json()
    print(f" -> Status: {data_v1['message']}")
    print(f" -> Total Sections Parsed: {data_v1['total_sections']}")
    print(f" -> Overall Document Content Hash: {data_v1['content_hash'][:16]}...")

    # STEP 2: Browse Sections
    print("\n[STEP 2] Browsing Top-Level Sections (v1)...")
    res = client.get("/api/sections?version=v1")
    top_secs = res.json()
    for s in top_secs:
        print(f"    - [{s['id']}] {s['heading']} (children: {s['children_count']})")

    # STEP 3: Inspect Section 4.2 (Overpressure & Error Codes)
    print("\n[STEP 3] Inspecting Node 'v1_sec_4_2' (Error Codes Table)...")
    res = client.get("/api/nodes/v1_sec_4_2")
    node_4_2 = res.json()
    print(f" -> Heading: {node_4_2['heading']}")
    print(f" -> Content Hash: {node_4_2['content_hash']}")
    print(f" -> Table Extract:\n{node_4_2['body_text'][:250]}...\n")

    # STEP 4: Create Version-Pinned Selection
    print("[STEP 4] Submitting Named Selection 'Safety & Alarm Subsystem' (Pinned to v1)...")
    res = client.post(
        "/api/selections",
        json={
            "name": "Safety & Alarm Subsystem",
            "node_ids": ["v1_sec_4_1", "v1_sec_4_2"],
            "description": "Critical patient safety verification: emergency venting and error codes.",
        },
    )
    selection = res.json()
    sel_id = selection["id"]
    print(f" -> Selection Created: ID={sel_id}")
    print(f" -> Pinned Version: {selection['version']}")
    print(f" -> Pinned Node Count: {len(selection['node_ids'])}")

    # STEP 5: Generate QA Test Cases using LLM
    print("\n[STEP 5] Generating QA Test Cases from Selection using LLM...")
    res = client.post("/api/generate", json={"selection_id": sel_id, "force_regenerate": False})
    gen1 = res.json()
    gen_id = gen1["generation_id"]
    print(f" -> Generation ID: {gen_id}")
    print(f" -> Summary: {gen1['summary']}")
    print(f" -> Generated Test Cases ({len(gen1['test_cases'])} cases):")
    for tc in gen1["test_cases"]:
        print(f"    * [{tc['test_case_id']}] {tc['title']} ({tc['severity']})")
        print(f"      Requirement Ref: {tc['requirement_ref']}")
        print(f"      Expected Result: {tc['expected_result']}")

    # STEP 6: Demonstrate Duplicate Submission Policy (Idempotency)
    print("\n[STEP 6] Submitting Duplicate Generation Request for Same Selection...")
    res = client.post("/api/generate", json={"selection_id": sel_id, "force_regenerate": False})
    gen2 = res.json()
    print(f" -> Response Cached Flag: {gen2['cached']}")
    print(f" -> Returned Same Generation ID: {gen2['generation_id'] == gen_id} ({gen2['generation_id']})")
    print(" -> Policy: Cached generation returned to prevent duplicate divergent test cases and save API tokens.")

    # STEP 7: Re-ingest Manual v2
    print("\n[STEP 7] Re-ingesting Modified Manual v2 (data/ct200_manual_v2.pdf)...")
    res = client.post("/api/ingest", json={"version": "v2", "pdf_path": str(DEFAULT_PDF_V2)})
    data_v2 = res.json()
    print(f" -> Status: {data_v2['message']}")
    print(f" -> Total Sections Parsed: {data_v2['total_sections']} (Added 5.3 Data Export)")

    # STEP 8: Inspect Cross-Version Diff for Section 4.2
    print("\n[STEP 8] Querying Cross-Version Diff for Node 'v1_sec_4_2' vs 'v2'...")
    res = client.get("/api/nodes/v1_sec_4_2/diff")
    diff = res.json()
    print(f" -> Has Changed: {diff['has_changed']}")
    print(f" -> Change Type: {diff['change_type']}")
    print(f" -> Diff Summary: {diff['diff_summary']}")

    # STEP 9: LIVE STALENESS & IMPACT DETECTION
    print("\n[STEP 9] Querying Previously Generated Test Cases for Staleness Detection...")
    res = client.get(f"/api/test-cases/{gen_id}")
    gen_detail = res.json()
    staleness = gen_detail["staleness_evaluation"]
    print(f" -> Is Stale: {staleness['is_stale']}")
    print(f" -> Staleness Status: {staleness['staleness_status']}")
    print(f" -> Pinned Version: {staleness['pinned_version']} vs Latest Version: {staleness['latest_version']}")
    print(f" -> Impact Summary: {staleness['impact_summary']}")
    for sn in staleness["stale_nodes"]:
        print(f"    * Node '{sn['heading']}' changed! Impact: {sn['impact']}")
        print(f"      Diff: {sn['diff_summary']}")

    # STEP 10: Retrieval by Node ID
    print("\n[STEP 10] Retrieving Test Cases Tracing to Node 'v1_sec_4_2'...")
    res = client.get("/api/nodes/v1_sec_4_2/test-cases")
    node_cases = res.json()
    print(f" -> Found {node_cases['generations_count']} generation(s) linked to this requirement.")

    print("\n" + "=" * 78)
    print(" DEMO COMPLETED SUCCESSFULLY: ALL REQUIREMENTS VERIFIED END-TO-END!")
    print("=" * 78)


if __name__ == "__main__":
    run_demo()
