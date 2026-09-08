"""
STEP 3 — Standalone Adzuna API test (runs outside Streamlit)
Run: .venv\Scripts\python.exe tests/test_adzuna.py
"""
import os, sys, json
from pathlib import Path
from dotenv import load_dotenv
import requests

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

app_id  = os.getenv("ADZUNA_APP_ID", "")
app_key = os.getenv("ADZUNA_APP_KEY", "")

print("=" * 60)
print("STEP 2 — Credential Check")
print("=" * 60)
print(f"  ADZUNA_APP_ID  loaded: {'YES' if app_id  else 'NO — EMPTY'}  (len={len(app_id)})")
print(f"  ADZUNA_APP_KEY loaded: {'YES' if app_key else 'NO — EMPTY'}  (len={len(app_key)})")

if not app_id or not app_key:
    print("\n  FAIL: One or both credentials missing. Cannot proceed.")
    sys.exit(1)
else:
    print("  PASS: Both credentials present.\n")

print("=" * 60)
print("STEP 3 — Raw Adzuna API Call (IT / Pune / 7 jobs)")
print("=" * 60)

url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
params = {
    "app_id":           app_id,
    "app_key":          app_key,
    "results_per_page": 7,
    "what":             "Software Developer Python React",
    "where":            "Pune",
    "content-type":     "application/json",
}

try:
    print(f"  GET {url}")
    print(f"  Params (keys): {list(params.keys())}\n")
    r = requests.get(url, params=params, timeout=12)
    print(f"  HTTP Status Code : {r.status_code}")
    print(f"  Content-Type     : {r.headers.get('Content-Type','n/a')}")

    if r.status_code == 200:
        data = r.json()
        total  = data.get("count", "n/a")
        results = data.get("results", [])
        print(f"  Total jobs count : {total}")
        print(f"  Results in page  : {len(results)}")
        if results:
            j = results[0]
            print(f"\n  First result title      : {j.get('title','n/a')}")
            print(f"  First result id         : {j.get('id','n/a')}")
            desc = j.get('description','')
            print(f"  First result desc chars : {len(desc)}")
            print(f"  Description preview     : {desc[:150]}")
        print("\n  PASS  API call returned valid data.")
    else:
        print(f"\n  Response body:\n{r.text[:500]}")
        print(f"\n  FAIL  Unexpected status {r.status_code}")

except requests.exceptions.ConnectionError as e:
    print(f"  FAIL  Network ConnectionError: {e}")
except requests.exceptions.Timeout:
    print("  FAIL  Request timed out after 12 seconds")
except Exception as e:
    print(f"  FAIL  Unexpected exception: {type(e).__name__}: {e}")
    import traceback; traceback.print_exc()
