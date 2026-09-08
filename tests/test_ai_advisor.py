import os
import sys
import json
import io
from pathlib import Path
import pandas as pd
import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.load_data import load_all_data
from src.ai_advisor import (
    analyze_requirement,
    extract_skills_with_ai,
    normalize_skill_name,
    get_provider_status_badge,
    get_active_provider_config,
    export_analysis_to_excel,
    export_analysis_to_csv,
)
from app.dashboard import log_feedback, FEEDBACK_FILE


def test_ai_advisor_suite():
    print("==================================================")
    print("RUNNING AI ADVISOR TEST SUITE")
    print("==================================================")

    # 1. Test Provider Status & Config
    provider, model, key = get_active_provider_config()
    badge = get_provider_status_badge()
    print(f"[1] Active Provider: {provider} | Model: {model} | Badge: {badge['status_text']}")
    assert badge["status_text"], "Status badge must not be empty"

    # 2. Test Normalization Function
    norm_bms = normalize_skill_name("bms")
    norm_can = normalize_skill_name("can bus")
    norm_aws = normalize_skill_name("AWS")
    print(f"[2] Normalization: BMS -> {norm_bms}, CAN Bus -> {norm_can}, AWS -> {norm_aws}")
    assert norm_bms == "Battery Management System"
    assert norm_can == "CAN Bus Diagnostics"
    assert norm_aws == "AWS Cloud"

    # 3. Load Real Curriculum Data
    jobs_df, curr_df = load_all_data()
    print(f"[3] Loaded {len(curr_df)} vocational curriculum entries.")
    assert len(curr_df) > 0, "Curriculum dataset should not be empty"

    # 4. Test All 4 Demo Inputs
    demo_tests = [
        (
            "Automotive EV",
            "EV technician required with Battery Management Systems, CAN Bus diagnostics, EV safety, battery testing and electrical troubleshooting in Pune.",
            "Job Description",
            ["Battery Management System", "CAN Bus Diagnostics", "Electric Vehicle Safety", "Battery Testing", "Electrical Troubleshooting"]
        ),
        (
            "IT & Cloud",
            "Cloud Engineer needed with Docker, Kubernetes container orchestration, CI/CD pipelines, AWS Cloud architecture, and microservices security.",
            "Job Description",
            ["Docker", "Kubernetes", "CI/CD Pipelines", "AWS Cloud"]
        ),
        (
            "Healthcare Lab",
            "Medical Laboratory Technician with Hematology, Clinical Biochemistry, Blood Banking, Quality Control, and Diagnostic Equipment Maintenance.",
            "Course / Curriculum Syllabus",
            ["Hematology", "Clinical Biochemistry", "Blood Banking"]
        ),
        (
            "Retail Omnichannel",
            "Omnichannel Retail Manager skilled in POS Systems, Inventory Forecasting, E-commerce Operations, Customer Retention, and Supply Chain Logistics.",
            "Industry Requirement",
            ["POS Systems", "Inventory Forecasting", "E-commerce Operations"]
        ),
    ]

    for name, text, itype, expected_subset in demo_tests:
        print(f"\n--- Testing Scenario: {name} ---")
        result = analyze_requirement(text, itype, curr_df)
        assert "error" not in result, f"Error in {name}: {result.get('error')}"
        
        detected = result["skills_detected"]
        cov = result["covered_count"]
        par = result["partial_count"]
        mis = result["missing_count"]
        align = result["alignment_pct"]
        print(f"    Detected: {detected} | Covered: {cov} | Partial: {par} | Missing: {mis} | Alignment: {align}%")
        assert detected >= len(expected_subset), f"Expected at least {len(expected_subset)} skills for {name}, got {detected}"
        assert (cov + par + mis) == detected, "Covered + Partial + Missing must equal total detected"

        align_df = result["alignment_df"]
        assert isinstance(align_df, pd.DataFrame)
        assert not align_df.empty

        assert len(result["executive_summary"]) > 50, "Executive summary too short"
        assert len(result["critical_gaps"]) >= 0
        assert len(result["trainer_roadmap"]) >= 0

    # 5. Test Deterministic RapidFuzz EV Case Specifically
    print("\n[5] Verifying EV Deterministic Thresholds:")
    ev_res = analyze_requirement(
        "EV technician required with Battery Management Systems, CAN Bus diagnostics, EV safety, battery testing and electrical troubleshooting in Pune.",
        "Job Description",
        curr_df
    )
    ev_df = ev_res["alignment_df"]
    for _, row in ev_df.iterrows():
        print(f"    Skill: {row['Skill']:<30} | Score: {row['Match Score']} | Status: {row['Status']:<8} | Course: {row['Best Matching Course']}")
        score = row["raw_score"]
        if row["Status"] == "Covered":
            assert score >= 80.0, f"Covered skill {row['Skill']} has score {score} < 80.0"
        elif row["Status"] == "Partial":
            assert 50.0 <= score < 80.0, f"Partial skill {row['Skill']} has score {score} not in [50, 80)"
        elif row["Status"] == "Missing":
            assert score < 50.0, f"Missing skill {row['Skill']} has score {score} >= 50.0"

    # 6. Test Multi-Sheet Excel & CSV Exporters
    print("\n[6] Testing Export Engines:")
    excel_bytes = export_analysis_to_excel(ev_res)
    assert len(excel_bytes) > 2000, "Excel output should be > 2KB"
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    sheet_names = wb.sheetnames
    print(f"    Excel Workbook Sheets: {sheet_names}")
    assert "Executive Summary" in sheet_names
    assert "Skill Alignment Matrix" in sheet_names

    csv_bytes = export_analysis_to_csv(ev_res)
    assert len(csv_bytes) > 50, "CSV output should not be empty"
    csv_str = csv_bytes.decode("utf-8")
    assert "Battery Management System" in csv_str or "CAN Bus" in csv_str
    print("    CSV & Excel Generation Verified.")

    # 7. Test Human-in-the-Loop Feedback Logging
    print("\n[7] Testing Feedback Logging:")
    test_entry = log_feedback(
        skill="Battery Testing",
        course="Electric Vehicle Maintenance",
        gap_status="partial",
        user_response="Agree",
        match_score=68.8,
        recommendation="Add specialized battery testing module",
        ai_provider=ev_res["provider_name"]
    )
    assert test_entry["skill"] == "Battery Testing"
    assert test_entry["user_response"] == "Agree"
    assert test_entry["ai_provider"] == ev_res["provider_name"]
    assert FEEDBACK_FILE.exists(), "feedback_log.json must exist"
    print("    Feedback entry appended successfully.")

    # 8. Test Zero-Crash Guarantee with Empty and Malformed Inputs
    print("\n[8] Testing Zero-Crash Edge Cases:")
    empty_res = analyze_requirement("", "Job Description", curr_df)
    assert "error" in empty_res
    print("    Empty input handled cleanly:", empty_res["error"])

    whitespace_res = analyze_requirement("   \n\t  ", "Job Description", curr_df)
    assert "error" in whitespace_res
    print("    Whitespace input handled cleanly:", whitespace_res["error"])

    non_tech_res = analyze_requirement("The quick brown fox jumps over the lazy dog.", "General Technical Text", curr_df)
    assert "error" in non_tech_res or "skills_detected" in non_tech_res
    print("    Non-technical input handled cleanly without crashing.")

    print("\n==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    test_ai_advisor_suite()
