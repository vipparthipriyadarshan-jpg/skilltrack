import sys
from pathlib import Path

# Add project root to sys.path so 'src' can be imported when running tests directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.load_data import load_jobs_data
from src.skill_extractor import extract_skills


def test_extractor_on_all_jobs():
    jobs_df = load_jobs_data()
    assert jobs_df is not None, "Failed to load jobs dataset"
    assert len(jobs_df) == 20, f"Expected 20 jobs, found {len(jobs_df)}"

    print(f"\n{'=' * 115}")
    print(f"{'JOB ID':<8} | {'SECTOR':<12} | {'JOB TITLE':<35} | {'EXTRACTED SKILLS'}")
    print(f"{'=' * 115}")

    for idx, row in jobs_df.iterrows():
        job_id = row["job_id"]
        sector = row["sector"]
        title = row["job_title"]
        desc = row["job_description"]

        skills = extract_skills(desc)
        skills_str = ", ".join(skills) if skills else "[NO SKILLS DETECTED]"

        print(f"{job_id:<8} | {sector:<12} | {title:<35} | {skills_str}")
        assert len(skills) > 0, f"No skills extracted for job {job_id}: {title}"

    print(f"{'=' * 115}\n")
    print(f"Successfully processed all {len(jobs_df)} jobs with extracted skills!")


if __name__ == "__main__":
    test_extractor_on_all_jobs()
