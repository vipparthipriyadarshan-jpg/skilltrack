import sys, os, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

print("--- I1: Searching for hardcoded absolute paths ---")
violations = []
abs_pattern = re.compile(r'(?:[A-Za-z]:[\\/]|/(?:Users|home|root)/)')

for folder in ["src", "app"]:
    for py_file in (ROOT / folder).rglob("*.py"):
        lines = py_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for lineno, line in enumerate(lines, 1):
            s = line.strip()
            if s.startswith("#") or s.startswith('"""') or s.startswith("'''"):
                continue
            if abs_pattern.search(line) and not ("http://" in line or "https://" in line):
                violations.append((py_file.name, lineno, s[:80]))

print(f"Violations found: {len(violations)}")
for f, l, content in violations:
    print(f"  {f}:{l} -> {content}")
assert len(violations) == 0, f"Found {len(violations)} hardcoded path violations!"
print("I1 PASS: Zero hardcoded absolute paths found in src/ or app/.")

print("\n--- I2: Validating requirements and launch readiness ---")
req_file = ROOT / "requirements.txt"
assert req_file.exists(), "requirements.txt missing"
req_text = req_file.read_text()
expected_deps = ["streamlit", "pandas", "spacy", "scikit-learn", "python-dotenv", "rapidfuzz", "requests"]
for dep in expected_deps:
    assert dep in req_text, f"Missing {dep} in requirements.txt"
print("I2 PASS: All core dependencies explicitly specified in requirements.txt.")

print("\n--- I3: Graceful missing data handling test ---")
jobs_path = ROOT / "data" / "jobs_sample.csv"
temp_hidden_path = ROOT / "data" / "_jobs_sample_temp_hidden.csv"

try:
    # Temporarily hide jobs_sample.csv
    jobs_path.rename(temp_hidden_path)
    print("  Temporarily hidden jobs_sample.csv...")
    
    from src.load_data import load_all_data
    jobs_data, curr_data = load_all_data()
    print(f"  load_all_data() result when CSV missing: jobs={jobs_data}, curr={type(curr_data)}")
    assert jobs_data is None, "Expected None when CSV is missing"
    print("  Confirmed load_all_data() returns None gracefully without crashing.")
finally:
    # Always restore original file
    if temp_hidden_path.exists() and not jobs_path.exists():
        temp_hidden_path.rename(jobs_path)
        print("  Restored jobs_sample.csv successfully.")

assert jobs_path.exists(), "jobs_sample.csv was not restored!"
print("I3 PASS: App handles missing CSV gracefully and file is safely restored.")

print("\n>>> SECTION I: 100% PASS <<<")
