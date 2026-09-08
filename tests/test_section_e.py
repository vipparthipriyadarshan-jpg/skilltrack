import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.live_fetcher import fetch_live_jobs_adzuna
from src.load_data import load_all_data
from src.demand_scorer import compute_demand
from src.gap_detector import detect_gaps
import pandas as pd

print("--- E1 & E2 & E3: Testing Live Fetch & Pipeline Ingestion ---")
new_jobs, err = fetch_live_jobs_adzuna("IT", "Pune", count=7)
if err:
    print(f"FAIL: {err}")
    sys.exit(1)

print(f"PASS: Ingested {len(new_jobs)} live job postings from Adzuna")
print(f"Columns: {list(new_jobs.columns)}")
for i, title in enumerate(new_jobs['job_title'], 1):
    print(f"  {i}. {title}")

# Simulate session state merge and pipeline rerun (E3)
baseline_jobs, curr = load_all_data()
combined_jobs = pd.concat([baseline_jobs, new_jobs], ignore_index=True)
print(f"Combined Jobs: {len(baseline_jobs)} baseline + {len(new_jobs)} live = {len(combined_jobs)} total")
assert len(combined_jobs) == len(baseline_jobs) + len(new_jobs)

# Verify pipeline processes new combined jobs
demand = compute_demand(combined_jobs)
gaps = detect_gaps(demand, curr)
print(f"Pipeline output with live data: {len(demand)} skills, {len(gaps)} gap records")
assert len(demand) >= 99
print("E1, E2, E3 PASS: Real data ingested, merged, and processed by pipeline cleanly.")

print("\n--- E4: Deliberately Broken API Key Test ---")
# Temporarily set invalid credentials in environment
orig_id = os.environ.get("ADZUNA_APP_ID")
orig_key = os.environ.get("ADZUNA_APP_KEY")

try:
    os.environ["ADZUNA_APP_ID"] = "invalid_id_9999"
    os.environ["ADZUNA_APP_KEY"] = "invalid_key_8888"
    
    broken_jobs, broken_err = fetch_live_jobs_adzuna("IT", "Pune", count=5)
    print(f"Broken key result: jobs={broken_jobs}, error message='{broken_err}'")
    assert broken_jobs is None, "Should not return data with invalid key"
    assert broken_err is not None, "Should return an error message"
    assert "authentication failed" in broken_err.lower() or "401" in broken_err or "403" in broken_err, f"Unexpected error msg: {broken_err}"
    print("E4 PASS: Clear, friendly authentication error returned instead of crash.")
finally:
    # Always restore original credentials
    if orig_id is not None:
        os.environ["ADZUNA_APP_ID"] = orig_id
    if orig_key is not None:
        os.environ["ADZUNA_APP_KEY"] = orig_key

print("\n>>> SECTION E: 100% PASS <<<")
