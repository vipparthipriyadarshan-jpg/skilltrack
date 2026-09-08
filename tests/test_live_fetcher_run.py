import sys
from pathlib import Path
sys.path.insert(0, str(Path(".").resolve()))
from src.live_fetcher import fetch_live_jobs_adzuna, generate_demo_live_jobs

sectors = ["IT", "Automotive", "Textile", "Healthcare", "Construction", "Retail/E-commerce"]
for s in sectors:
    df, err = fetch_live_jobs_adzuna(s, "Pune", count=3)
    if df is not None and not df.empty:
        print(f"[LIVE API PASS] {s:18}: {len(df)} jobs fetched! First: {df.iloc[0]['job_title'][:40]}")
    else:
        print(f"[LIVE API FAIL] {s:18}: {err}")

    demo_df = generate_demo_live_jobs(s, "Pune", count=2)
    print(f"  [DEMO PASS]   {s:18}: {len(demo_df)} demo jobs. First: {demo_df.iloc[0]['job_title'][:40]}")
