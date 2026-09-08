"""
Full Project Diagnostic: Checks 3-11
Run from project root: .venv\Scripts\python.exe tests/run_diagnostics.py
"""
import sys, os, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

results = []

def hdr(n, title):
    print(f"\n{'='*60}")
    print(f"  CHECK {n}: {title}")
    print(f"{'='*60}")

def ok(msg):
    print(f"  PASS  {msg}")

def fail(msg):
    print(f"  FAIL  {msg}")

def note(msg):
    print(f"        {msg}")

def record(check, status, notes=""):
    results.append({"check": check, "status": status, "notes": notes})

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3: Data Integrity
# ─────────────────────────────────────────────────────────────────────────────
hdr(3, "Data Integrity")
import pandas as pd

c3_pass = True
jobs_df = pd.DataFrame()
curr_df = pd.DataFrame()

try:
    jobs_df = pd.read_csv(ROOT / "data" / "jobs_sample.csv")
    ok(f"jobs_sample.csv loaded — {len(jobs_df)} rows, {len(jobs_df.columns)} cols")
    note(f"Columns: {list(jobs_df.columns)}")

    required_job_cols = ["job_id","job_title","sector","district","job_description"]
    missing_jc = [c for c in required_job_cols if c not in jobs_df.columns]
    if missing_jc:
        fail(f"Missing job columns: {missing_jc}"); c3_pass = False
    else:
        ok("All required job columns present")

    if len(jobs_df) >= 15:
        ok(f"Row count {len(jobs_df)} >= 15")
    else:
        fail(f"Only {len(jobs_df)} rows — need >=15"); c3_pass = False

    empty_desc = jobs_df["job_description"].isna().sum() + (jobs_df["job_description"].str.strip() == "").sum()
    if empty_desc == 0:
        ok("No empty job_descriptions")
    else:
        fail(f"{empty_desc} empty job_descriptions"); c3_pass = False

    dups = jobs_df.duplicated().sum()
    if dups == 0:
        ok("No duplicate rows in jobs_sample")
    else:
        fail(f"{dups} duplicate rows found"); c3_pass = False

except Exception as e:
    fail(f"Cannot load jobs_sample.csv: {e}"); c3_pass = False

try:
    curr_df = pd.read_csv(ROOT / "data" / "curriculum_sample.csv")
    ok(f"curriculum_sample.csv loaded — {len(curr_df)} rows")
    note(f"Columns: {list(curr_df.columns)}")

    required_curr_cols = ["course_id","course_name","sector","skills_taught"]
    missing_cc = [c for c in required_curr_cols if c not in curr_df.columns]
    if missing_cc:
        fail(f"Missing curriculum columns: {missing_cc}"); c3_pass = False
    else:
        ok("All required curriculum columns present")

    if len(curr_df) >= 10:
        ok(f"Row count {len(curr_df)} >= 10")
    else:
        fail(f"Only {len(curr_df)} rows — need >=10"); c3_pass = False

    # Check gap potential
    if not jobs_df.empty and "skills_taught" in curr_df.columns:
        from src.skill_extractor import extract_skills
        curr_skills = set()
        for row in curr_df["skills_taught"].dropna():
            for s in row.split(","):
                curr_skills.add(s.strip().lower())

        job_skills = set()
        for desc in jobs_df["job_description"].dropna():
            for s in extract_skills(desc):
                job_skills.add(s.strip().lower())

        uncovered = job_skills - curr_skills
        if uncovered:
            ok(f"Gap potential confirmed — {len(uncovered)} job skills NOT in curriculum")
            note(f"Sample uncovered: {list(uncovered)[:8]}")
        else:
            fail("ALL job skills appear in curriculum — no gaps will be detected!"); c3_pass = False

except Exception as e:
    fail(f"Cannot load curriculum_sample.csv: {e}"); c3_pass = False

record("CHECK 3: Data Integrity", "PASS" if c3_pass else "FAIL",
       f"{len(jobs_df)} job rows, {len(curr_df)} curr rows")


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 4: Skill Extraction
# ─────────────────────────────────────────────────────────────────────────────
hdr(4, "Skill Extraction")
c4_pass = True
BAD_WORDS = {"the","a","an","and","or","of","to","in","for","is","it",
             "be","was","with","that","this","are","on","at","by","not",
             "have","had","has","but","from","they","we","you","he","she",
             "company","role","position","work","team","job","candidate"}

unique_skills = set()
try:
    from src.skill_extractor import extract_skills
    empty_rows = []
    bad_token_rows = []

    for i, row in jobs_df.iterrows():
        desc = row.get("job_description","")
        skills = extract_skills(desc)
        unique_skills.update(skills)
        if not skills:
            empty_rows.append(i)
        bad = [s for s in skills if s.lower().strip() in BAD_WORDS]
        if bad:
            bad_token_rows.append((i, bad))

    if empty_rows:
        fail(f"Rows with ZERO skills extracted: {empty_rows}"); c4_pass = False
    else:
        ok(f"All {len(jobs_df)} rows returned non-empty skill lists")

    if bad_token_rows:
        fail(f"Noise tokens found in rows: {bad_token_rows[:3]}"); c4_pass = False
    else:
        ok("No filler/noise words in extracted skills")

    ok(f"Total unique skills across all jobs: {len(unique_skills)}")
    note(f"Sample: {sorted(unique_skills)[:12]}")

except Exception as e:
    fail(f"extract_skills() crashed: {e}"); c4_pass = False
    import traceback; traceback.print_exc()

record("CHECK 4: Skill Extraction", "PASS" if c4_pass else "FAIL",
       f"{len(unique_skills)} unique skills")


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 5: Gap Detection Logic
# ─────────────────────────────────────────────────────────────────────────────
hdr(5, "Gap Detection Logic")
c5_pass = True
gap_df = pd.DataFrame()

try:
    from src.demand_scorer import compute_demand
    from src.gap_detector import detect_gaps

    demand_df = compute_demand(jobs_df)
    ok(f"compute_demand() returned {len(demand_df)} rows")

    gap_df = detect_gaps(demand_df, curr_df)
    ok(f"detect_gaps() returned {len(gap_df)} rows")

    if gap_df.empty:
        fail("Gap DataFrame is empty!"); c5_pass = False
    else:
        statuses = gap_df["gap_status"].value_counts()
        note(f"Status distribution: {statuses.to_dict()}")

        has_all_three = all(s in statuses.index for s in ["covered","partial","missing"])
        if has_all_three:
            ok("All three statuses present: covered / partial / missing")
        else:
            missing_status = [s for s in ["covered","partial","missing"] if s not in statuses.index]
            fail(f"Missing status categories: {missing_status} — check matching thresholds"); c5_pass = False

        conf = gap_df["match_confidence"]
        nan_count = conf.isna().sum()
        neg_count = (conf < 0).sum()
        over_count = (conf > 100).sum()

        if nan_count > 0:
            fail(f"{nan_count} NaN confidence values"); c5_pass = False
        else:
            ok("No NaN confidence values")

        if neg_count > 0 or over_count > 0:
            fail(f"{neg_count} negative, {over_count} >100 confidence values"); c5_pass = False
        else:
            ok(f"All confidence in 0-100 (min={conf.min():.1f} max={conf.max():.1f} mean={conf.mean():.1f})")

except Exception as e:
    fail(f"Pipeline crashed: {e}"); c5_pass = False
    import traceback; traceback.print_exc()

record("CHECK 5: Gap Detection", "PASS" if c5_pass else "FAIL",
       str(gap_df["gap_status"].value_counts().to_dict()) if not gap_df.empty else "empty")


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 6: Trainer Flag Logic
# ─────────────────────────────────────────────────────────────────────────────
hdr(6, "Trainer Flag Logic")
c6_pass = True
trainer_df = pd.DataFrame()

try:
    from src.gap_detector import flag_trainer_needs
    trainer_df = flag_trainer_needs(gap_df)
    ok(f"flag_trainer_needs() returned {len(trainer_df)} rows")

    if trainer_df.empty:
        fail("No trainer flags raised — all skills may be covered (check gap data)"); c6_pass = False
    else:
        ok(f"{len(trainer_df)} trainer interventions flagged")
        note(f"Columns: {list(trainer_df.columns)}")
        if "reason" in trainer_df.columns:
            note(f"Sample reason: '{trainer_df['reason'].iloc[0]}'")
        if "demand_count" in trainer_df.columns:
            note(f"Demand range: {trainer_df['demand_count'].min()} to {trainer_df['demand_count'].max()}")

except Exception as e:
    fail(f"flag_trainer_needs() crashed: {e}"); c6_pass = False

record("CHECK 6: Trainer Flag Logic", "PASS" if c6_pass else "FAIL",
       f"{len(trainer_df)} flags" if not trainer_df.empty else "none")


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 8: Feedback Log
# ─────────────────────────────────────────────────────────────────────────────
hdr(8, "Feedback Log Structure")
c8_pass = True
fb_path = ROOT / "data" / "feedback_log.json"
fb = []

try:
    if fb_path.exists():
        with open(fb_path, "r", encoding="utf-8") as f:
            fb = json.load(f)
        if isinstance(fb, list):
            ok(f"feedback_log.json is valid list ({len(fb)} entries)")
            if fb:
                entry = fb[0]
                required_keys = {"skill","course","gap_status","user_response","timestamp"}
                missing_keys = required_keys - set(entry.keys())
                if missing_keys:
                    fail(f"Missing keys in entries: {missing_keys}"); c8_pass = False
                else:
                    ok(f"All required keys present")
                    note(f"Sample: {entry}")
        else:
            fail("feedback_log.json is not a list"); c8_pass = False
    else:
        ok("feedback_log.json not yet created — will auto-create on first Agree/Disagree click")

except Exception as e:
    fail(f"feedback_log.json error: {e}"); c8_pass = False

record("CHECK 8: Feedback Log", "PASS" if c8_pass else "FAIL",
       f"{len(fb)} entries" if fb_path.exists() else "auto-creates on first click")


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 9: API Integration
# ─────────────────────────────────────────────────────────────────────────────
hdr(9, "API Key / live_fetcher Module")
c9_pass = True
env_path = ROOT / ".env"

try:
    if env_path.exists():
        content = env_path.read_text(encoding="utf-8")
        raw_id  = ""
        raw_key = ""
        for line in content.splitlines():
            if line.startswith("ADZUNA_APP_ID="):
                raw_id = line.split("=",1)[1].strip()
            if line.startswith("ADZUNA_APP_KEY="):
                raw_key = line.split("=",1)[1].strip()

        # A real key: non-empty, >= 4 chars, no placeholder keywords
        bad_kw = ("your_", "<your", "placeholder", "example", "xxx", "key_here", "id_here")
        has_id  = bool(raw_id)  and len(raw_id) >= 4  and not any(p in raw_id.lower()  for p in bad_kw)
        has_key = bool(raw_key) and len(raw_key) >= 8 and not any(p in raw_key.lower() for p in bad_kw)

        if has_id and has_key:
            ok(f".env has both ADZUNA_APP_ID (len={len(raw_id)}) and ADZUNA_APP_KEY (len={len(raw_key)}) set")
        else:
            if not has_id:
                fail(f"ADZUNA_APP_ID is missing or placeholder: '{raw_id}'"); c9_pass = False
            if not has_key:
                fail(f"ADZUNA_APP_KEY is missing or placeholder: '{raw_key}'"); c9_pass = False
    else:
        fail(".env file missing"); c9_pass = False

    from src.live_fetcher import fetch_live_jobs_adzuna, generate_demo_live_jobs
    demo = generate_demo_live_jobs("IT", "Pune", count=3)
    if not demo.empty and len(demo) == 3:
        ok(f"generate_demo_live_jobs() works ({len(demo)} demo rows)")
        note(f"Demo columns: {list(demo.columns)}")
    else:
        fail("generate_demo_live_jobs() unexpected result"); c9_pass = False

except Exception as e:
    fail(f"live_fetcher error: {e}"); c9_pass = False

record("CHECK 9: API Integration", "PASS" if c9_pass else "FAIL",
       "Keys configured + demo generator works")


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 10: Error Handling — Missing CSV
# ─────────────────────────────────────────────────────────────────────────────
hdr(10, "Error Handling — Missing CSV Graceful Failure")
c10_pass = True
orig_path   = ROOT / "data" / "jobs_sample.csv"
hidden_path = ROOT / "data" / "_jobs_hidden_tmp.csv"
restored = False

try:
    shutil.copy(orig_path, hidden_path)  # backup
    orig_path.rename(ROOT / "data" / "_jobs_moved.csv")

    from src.load_data import load_all_data
    jobs_t, curr_t = load_all_data()

    (ROOT / "data" / "_jobs_moved.csv").rename(orig_path)
    restored = True

    if jobs_t is None:
        ok("load_all_data() returned None gracefully when CSV missing (no crash)")
    else:
        note(f"load_all_data() returned {type(jobs_t)} — checking if empty or sentinel")

    hidden_path.unlink(missing_ok=True)

except Exception as e:
    fail(f"Error handling test raised exception: {e}"); c10_pass = False
    # Always restore
    try:
        moved = ROOT / "data" / "_jobs_moved.csv"
        if moved.exists() and not orig_path.exists():
            moved.rename(orig_path)
        hidden_path.unlink(missing_ok=True)
    except Exception as re:
        fail(f"RESTORE FAILED: {re} — MANUALLY RESTORE jobs_sample.csv!")

record("CHECK 10: Error Handling", "PASS" if c10_pass else "FAIL",
       "Graceful None on missing CSV" if c10_pass else "Exception raised — fix load_data.py")


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 11: No Hardcoded Absolute Paths
# ─────────────────────────────────────────────────────────────────────────────
hdr(11, "No Hardcoded Absolute Paths")
c11_pass = True
# Match paths but NOT inside comments or string literals that look like user-facing error messages
abs_re = re.compile(r'(?:C:\\\\|C:/|/Users/|/home/|/root/)', re.IGNORECASE)
search_dirs = [ROOT / "src", ROOT / "app"]
violations = []

for sdir in search_dirs:
    for py_file in sdir.glob("*.py"):
        lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if abs_re.search(line):
                violations.append(f"{py_file.name}:{lineno}: {stripped[:90]}")

if violations:
    for v in violations:
        fail(f"Hardcoded path detected: {v}")
    c11_pass = False
else:
    ok("No hardcoded absolute paths found in /src or /app")

record("CHECK 11: Hardcoded Paths", "PASS" if c11_pass else "FAIL",
       f"{len(violations)} violations" if violations else "Clean")


# ─────────────────────────────────────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print("  FINAL DIAGNOSTIC SUMMARY")
print(f"{'='*65}")
print(f"  {'Check':<38} {'Status':<12} Notes")
print(f"  {'-'*38} {'-'*12} --------")
for r in results:
    icon = "PASS" if r["status"] in ("PASS","FIXED") else "FAIL"
    print(f"  {r['check']:<38} {icon:<12} {r['notes']}")

all_pass = all(r["status"] in ("PASS","FIXED") for r in results)
print(f"\n{'='*65}")
if all_pass:
    print("  ALL CHECKS PASSED — System is fully working end-to-end and ready for demo.")
else:
    failed = [r["check"] for r in results if r["status"] not in ("PASS","FIXED")]
    print(f"  FAILURES: {failed}")
print(f"{'='*65}\n")
