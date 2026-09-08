"""Step 6 pre-check: verify the full fetch->pipeline flow works end-to-end"""
import sys
from pathlib import Path
ROOT = Path('.').resolve()
sys.path.insert(0, str(ROOT))

import pandas as pd
from src.live_fetcher import fetch_live_jobs_adzuna
from src.load_data import load_all_data
from src.demand_scorer import compute_demand
from src.gap_detector import detect_gaps, flag_trainer_needs

print("=== Simulating: Fetch Live Jobs Now button click ===")
print("Sector=IT, District=Pune, Count=7")
print()

new_jobs, err = fetch_live_jobs_adzuna("IT", "Pune", 7)
if err:
    print(f"FAIL  Error from fetcher: {err}")
    sys.exit(1)

print(f"PASS  fetch_live_jobs_adzuna returned {len(new_jobs)} rows")
print(f"      Columns: {list(new_jobs.columns)}")
print("      Titles:")
for t in new_jobs["job_title"].tolist():
    print(f"        - {t}")
print()

baseline_jobs, curr_df = load_all_data()
combined = pd.concat([baseline_jobs, new_jobs], ignore_index=True)
print(f"PASS  Combined jobs: {len(combined)} rows ({len(baseline_jobs)} baseline + {len(new_jobs)} live)")

demand_df = compute_demand(combined)
gap_df    = detect_gaps(demand_df, curr_df)
trainer   = flag_trainer_needs(gap_df)
statuses  = gap_df["gap_status"].value_counts().to_dict()
print(f"PASS  Pipeline complete:")
print(f"      demand rows : {len(demand_df)}")
print(f"      gap rows    : {len(gap_df)}")
print(f"      statuses    : {statuses}")
print(f"      trainer flags: {len(trainer)}")
print()
print("All good — fix is valid. Streamlit will be started next.")
