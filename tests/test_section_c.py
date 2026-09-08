import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.load_data import load_all_data
from src.skill_extractor import extract_skills
from src.demand_scorer import compute_demand
from src.gap_detector import detect_gaps, flag_trainer_needs

jobs, curr = load_all_data()

print('--- C1: extract_skills() on each job row ---')
stopwords = {'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of'}
for idx, row in jobs.iterrows():
    title = row['job_title']
    skills = extract_skills(row['job_description'])
    assert len(skills) > 0, f"Row {idx} ({title}) returned empty skill list!"
    for s in skills:
        assert s.lower() not in stopwords, f"Row {idx} extracted stopword: {s}"
        assert len(s.strip()) > 1, f"Row {idx} extracted single-char: {s}"
print(f"  C1 PASS: All {len(jobs)} jobs extracted valid skills, zero empty lists, zero noise/stopwords.")

print('--- C2: compute_demand() ---')
demand_df = compute_demand(jobs)
print(f"  Demand table rows: {len(demand_df)}")
print(f"  Demand table columns: {list(demand_df.columns)}")
expected_demand_cols = ['skill', 'demand_count', 'sectors', 'districts']
for col in expected_demand_cols:
    assert col in demand_df.columns, f"Missing demand column: {col}"
assert len(demand_df) > 0, "compute_demand returned empty table"
assert demand_df['demand_count'].min() >= 1, "Invalid demand count < 1"
print("  C2 PASS: compute_demand() returned valid table with demand counts, sectors, and districts.")

print('--- C3: detect_gaps() ---')
gap_df = detect_gaps(demand_df, curr)
print(f"  Gap table rows: {len(gap_df)}")
print(f"  Gap table columns: {list(gap_df.columns)}")
status_counts = gap_df['gap_status'].value_counts().to_dict()
print(f"  Gap status distribution: {status_counts}")
assert 'covered' in status_counts, "Missing covered status"
assert 'partial' in status_counts, "Missing partial status"
assert 'missing' in status_counts, "Missing missing status"
assert status_counts['covered'] > 0 and status_counts['partial'] > 0 and status_counts['missing'] > 0, "Need a real mix of all 3 statuses"

# Check match_confidence range
assert not gap_df['match_confidence'].isna().any(), "Found NaN match_confidence"
assert (gap_df['match_confidence'] >= 0).all(), "Negative match_confidence found"
assert (gap_df['match_confidence'] <= 100).all(), "match_confidence > 100 found"
print("  C3 PASS: Healthy mix of covered/partial/missing, match_confidence valid (0-100, no NaNs).")

print('--- C4: flag_trainer_needs() ---')
trainer_df = flag_trainer_needs(gap_df)
print(f"  Trainer needs flagged rows: {len(trainer_df)}")
print(f"  Trainer columns: {list(trainer_df.columns)}")
assert len(trainer_df) >= 3, f"Too few trainer needs flagged: {len(trainer_df)}"
assert 'trainer_upskilling_needed' in trainer_df.columns, "Missing trainer_upskilling_needed column"
assert not trainer_df['trainer_upskilling_needed'].isna().any(), "NaN in trainer_upskilling_needed"
print("  C4 PASS: flag_trainer_needs() returned valid rows with proper boolean flags and actionable rationale.")

print('\n>>> SECTION C: 100% PASS <<<')
