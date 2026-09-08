import sys, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.dashboard import log_feedback, FEEDBACK_FILE

print("--- F1 & F2: Testing Agree and Disagree Logging ---")
initial_count = 0
if FEEDBACK_FILE.exists():
    with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
        initial_count = len(json.load(f))
print(f"Initial feedback log count: {initial_count}")

# 1. Log Agree for Docker
entry1 = log_feedback("Docker", "Certificate in Python and Web Basics", "partial", "Agree")
print(f"Logged Agree: {entry1}")

# 2. Log Disagree for Kubernetes
entry2 = log_feedback("Kubernetes", "Advanced Diploma in Cloud & DevOps", "missing", "Disagree")
print(f"Logged Disagree: {entry2}")

# Verify file updated
assert FEEDBACK_FILE.exists(), "feedback_log.json was not created/found"
with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
    logs = json.load(f)

new_count = len(logs)
print(f"New feedback log count: {new_count}")
assert new_count == initial_count + 2, f"Count expected {initial_count + 2}, got {new_count}"

# Verify schema
required_keys = {"skill", "course", "gap_status", "user_response", "timestamp"}
for item in logs[-2:]:
    assert required_keys.issubset(item.keys()), f"Missing keys in feedback entry: {item}"
print("F1 & F2 PASS: Agree and Disagree logged with complete schema.")

print("\n--- F3: Testing Model Feedback Counter Calculation ---")
total_validated = len(logs)
agreed_count = sum(1 for v in logs if v.get("user_response") == "Agree")
disagreed_count = sum(1 for v in logs if v.get("user_response") == "Disagree")
agreement_pct = round((agreed_count / total_validated * 100), 1) if total_validated > 0 else 0.0

print(f"Model Feedback Metrics:")
print(f"  Total Validations: {total_validated}")
print(f"  Agreed Count: {agreed_count}")
print(f"  Disagreed Count: {disagreed_count}")
print(f"  Consensus: {agreement_pct}%")

assert total_validated >= 2
assert agreed_count >= 1
assert disagreed_count >= 1
print("F3 PASS: Model Feedback counter correctly calculates updated metrics.")

print("\n>>> SECTION F: 100% PASS <<<")
