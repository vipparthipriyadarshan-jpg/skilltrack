import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.load_data import load_all_data
from src.demand_scorer import compute_demand
from src.gap_detector import detect_gaps, flag_trainer_needs


def main():
    jobs_df, curr_df = load_all_data()
    demand_df = compute_demand(jobs_df)
    gap_df = detect_gaps(demand_df, curr_df)
    trainer_df = flag_trainer_needs(gap_df)

    # Sort both tables by demand_count descending, then skill name
    gap_sorted = gap_df.sort_values(
        by=["demand_count", "skill"], ascending=[False, True]
    ).reset_index(drop=True)

    trainer_sorted = trainer_df.sort_values(
        by=["demand_count", "skill"], ascending=[False, True]
    ).reset_index(drop=True)

    print("\n" + "=" * 120)
    print("TABLE 1: CURRICULUM GAP ANALYSIS RESULTS (Sorted by demand_count descending)")
    print("=" * 120)
    print(
        f"{'SKILL':<36} | {'DEMAND':<6} | {'GAP STATUS':<10} | {'CONFIDENCE':<10} | {'MATCHED COURSE'}"
    )
    print("-" * 120)
    for _, row in gap_sorted.iterrows():
        print(
            f"{row['skill']:<36} | {row['demand_count']:<6} | {row['gap_status']:<10} | "
            f"{row['match_confidence']:<10.1f} | {row['matched_course']}"
        )

    print("\n" + "=" * 120)
    print("TABLE 2: TRAINER UPSKILLING NEEDS & RATIONALE (Sorted by demand_count descending)")
    print("=" * 120)
    print(f"{'SKILL':<36} | {'DEMAND':<6} | {'UPSKILL?':<8} | {'REASON'}")
    print("-" * 120)
    for _, row in trainer_sorted.iterrows():
        print(
            f"{row['skill']:<36} | {row['demand_count']:<6} | {str(row['trainer_upskilling_needed']):<8} | {row['reason']}"
        )
    print("=" * 120)


if __name__ == "__main__":
    main()
