import sys
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Optional
import pandas as pd

# Ensure repository root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.skill_extractor import extract_skills


def compute_demand(jobs_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Computes demand statistics for all skills mentioned across job postings.

    Args:
        jobs_df: DataFrame containing job postings with columns:
                 'job_description', 'sector', 'district'

    Returns:
        DataFrame with columns:
        - skill (str): Name of the extracted skill
        - demand_count (int): Total number of job postings requesting this skill
        - sectors (List[str]): Unique sectors where this skill was demanded
        - districts (List[str]): Unique districts where this skill was demanded
    """
    columns = ["skill", "demand_count", "sectors", "districts"]

    if jobs_df is None or jobs_df.empty:
        return pd.DataFrame(columns=columns)

    # Dictionary to aggregate demand data per skill
    skill_stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"demand_count": 0, "sectors": set(), "districts": set()}
    )

    for _, row in jobs_df.iterrows():
        desc = row["job_description"] if "job_description" in row else ""
        sector = row["sector"] if "sector" in row else "Unspecified"
        district = row["district"] if "district" in row else "Unspecified"

        if pd.isna(desc):
            continue

        extracted_skills = extract_skills(desc)
        if not extracted_skills:
            continue

        for skill in extracted_skills:
            skill_stats[skill]["demand_count"] += 1
            if pd.notna(sector) and str(sector).strip() and str(sector).strip() != "nan":
                skill_stats[skill]["sectors"].add(str(sector).strip())
            if pd.notna(district) and str(district).strip() and str(district).strip() != "nan":
                skill_stats[skill]["districts"].add(str(district).strip())

    records = []
    for skill, data in skill_stats.items():
        records.append(
            {
                "skill": skill,
                "demand_count": data["demand_count"],
                "sectors": sorted(list(data["sectors"])),
                "districts": sorted(list(data["districts"])),
            }
        )

    if not records:
        return pd.DataFrame(columns=columns)

    result_df = pd.DataFrame(records)
    # Sort by demand_count descending, then by skill name
    result_df = result_df.sort_values(
        by=["demand_count", "skill"], ascending=[False, True]
    ).reset_index(drop=True)

    return result_df[columns]


def main():
    from src.load_data import load_jobs_data

    print("=== Testing Demand Scorer ===")
    jobs_df = load_jobs_data()
    demand_df = compute_demand(jobs_df)

    print(f"\nTotal unique skills extracted: {len(demand_df)}")
    print(f"\nTop 15 Most Demanded Skills:")
    print("-" * 90)
    for _, row in demand_df.head(15).iterrows():
        print(
            f"{row['skill']:<36} | Count: {row['demand_count']} | "
            f"Sectors: {', '.join(row['sectors']):<12} | "
            f"Districts: {', '.join(row['districts'])}"
        )
    print("-" * 90)


if __name__ == "__main__":
    main()
