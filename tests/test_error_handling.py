import os
import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.load_data import load_jobs_data, load_curriculum_data, load_all_data
from src.skill_extractor import extract_skills
from src.demand_scorer import compute_demand
from src.gap_detector import detect_gaps, flag_trainer_needs
from src.live_fetcher import fetch_live_jobs_adzuna, generate_demo_live_jobs


def test_missing_csv_files():
    print("\n--- Test 1: Missing CSV Files ---")
    jobs = load_jobs_data(PROJECT_ROOT / "data" / "non_existent_file.csv")
    curr = load_curriculum_data(PROJECT_ROOT / "data" / "non_existent_file.csv")
    assert jobs is None, "Missing jobs file should return None"
    assert curr is None, "Missing curriculum file should return None"
    print("PASS: Missing CSV files handled safely without throwing exceptions.")


def test_empty_and_malformed_job_descriptions():
    print("\n--- Test 2: Empty, NaN, and Malformed Job Descriptions ---")
    edge_cases = [
        "",
        " ",
        None,
        float("nan"),
        12345,
        "   \n\t   ",
        "a",
        "Looking for a candidate with no mentioned skills whatsoever in this line.",
    ]
    for case in edge_cases:
        res = extract_skills(case)
        assert isinstance(res, list), f"Expected list for case {case!r}, got {type(res)}"
    
    # Test DataFrame with NaN and empty descriptions
    df_edge = pd.DataFrame({
        "job_id": ["J1", "J2", "J3", "J4"],
        "job_title": ["Dev", "Analyst", "Empty", "None"],
        "sector": ["IT", "IT", "Automotive", "Textile"],
        "district": ["Pune", "Nashik", "Nagpur", "Pune"],
        "job_description": [None, "", float("nan"), "Proficient in Python and React"],
    })
    demand_df = compute_demand(df_edge)
    assert not demand_df.empty, "Should extract skills from valid rows"
    assert "Python" in demand_df["skill"].values
    assert "React" in demand_df["skill"].values
    print("PASS: Empty, NaN, and numeric job descriptions handled cleanly.")


def test_skill_with_zero_matches():
    print("\n--- Test 3: Skill with Zero Matches Anywhere ---")
    # Demand with an esoteric or unaddressed skill
    mock_demand = pd.DataFrame([
        {"skill": "Quantum Computing Superposition", "demand_count": 3, "sectors": ["IT"], "districts": ["Pune"]},
        {"skill": "Interstellar Navigation", "demand_count": 1, "sectors": ["Automotive"], "districts": ["Nagpur"]},
    ])
    _, curr_df = load_all_data()
    gap_df = detect_gaps(mock_demand, curr_df)
    trainer_df = flag_trainer_needs(gap_df)

    assert len(gap_df) == 2
    # Verify that unmatched skill is handled gracefully as missing with "None" course
    for _, row in gap_df.iterrows():
        assert row["gap_status"] == "missing"
        assert row["matched_course"] == "None"
        assert row["match_confidence"] < 50.0

    assert len(trainer_df) == 2
    for _, row in trainer_df.iterrows():
        assert row["trainer_upskilling_needed"] is True
        assert "Critical Gap" in row["reason"]

    print("PASS: 0-matched skills correctly categorized as missing with actionable trainer flags.")


def test_broken_or_missing_api_key():
    print("\n--- Test 4: Broken, Missing, or Unauthorized API Key ---")
    # Case A: Missing key
    old_id = os.environ.get("ADZUNA_APP_ID")
    old_key = os.environ.get("ADZUNA_APP_KEY")
    if "ADZUNA_APP_ID" in os.environ:
        del os.environ["ADZUNA_APP_ID"]
    if "ADZUNA_APP_KEY" in os.environ:
        del os.environ["ADZUNA_APP_KEY"]

    df_none, err_msg = fetch_live_jobs_adzuna("IT", "Pune", 5)
    assert df_none is None
    assert err_msg is not None and "credentials not configured" in err_msg
    print(f"PASS (Missing Key): '{err_msg}'")

    # Case B: Broken / Invalid key
    os.environ["ADZUNA_APP_ID"] = "invalid_id_12345"
    os.environ["ADZUNA_APP_KEY"] = "invalid_key_67890"
    df_invalid, err_invalid = fetch_live_jobs_adzuna("IT", "Pune", 5)
    assert df_invalid is None
    assert err_invalid is not None
    print(f"PASS (Invalid Key): '{err_invalid}'")

    # Restore environment
    if old_id:
        os.environ["ADZUNA_APP_ID"] = old_id
    elif "ADZUNA_APP_ID" in os.environ:
        del os.environ["ADZUNA_APP_ID"]
    if old_key:
        os.environ["ADZUNA_APP_KEY"] = old_key
    elif "ADZUNA_APP_KEY" in os.environ:
        del os.environ["ADZUNA_APP_KEY"]

    # Case C: Demo live batch generator fallback
    demo_df = generate_demo_live_jobs("IT", "Pune", 5)
    assert len(demo_df) == 5
    assert list(demo_df.columns) == ["job_id", "job_title", "sector", "district", "job_description"]
    print("PASS (Demo Generator Fallback): Generated 5 structured live demo jobs.")


def main():
    print("==================================================")
    print("RUNNING COMPREHENSIVE DEFENSIVE ERROR-HANDLING TEST")
    print("==================================================")
    test_missing_csv_files()
    test_empty_and_malformed_job_descriptions()
    test_skill_with_zero_matches()
    test_broken_or_missing_api_key()
    print("\n==================================================")
    print("ALL DEFENSIVE ERROR-HANDLING TESTS PASSED (100% OK)")
    print("==================================================")


if __name__ == "__main__":
    main()
