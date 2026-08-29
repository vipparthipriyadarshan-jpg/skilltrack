import sys
from pathlib import Path
from typing import Optional
import pandas as pd
from rapidfuzz import fuzz

# Ensure repository root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def get_gap_status(confidence: float) -> str:
    """
    Determine gap status based on similarity score:
    - > 80: 'covered'
    - 50 to 80: 'partial'
    - < 50: 'missing'
    """
    if confidence > 80.0:
        return "covered"
    elif confidence >= 50.0:
        return "partial"
    else:
        return "missing"


def detect_gaps(
    demand_df: Optional[pd.DataFrame],
    curriculum_df: Optional[pd.DataFrame],
    similarity_threshold: float = 80.0,
) -> pd.DataFrame:
    """
    Detects skill gaps by matching in-demand skills against curriculum courses
    using rapidfuzz partial_ratio.

    Args:
        demand_df: DataFrame with columns ['skill', 'demand_count', ...]
        curriculum_df: DataFrame with columns ['course_id', 'course_name', 'sector', 'skills_taught']
        similarity_threshold: Threshold above which a skill is 'covered' (default: 80.0)

    Returns:
        DataFrame with columns:
        - skill (str)
        - demand_count (int)
        - matched_course (str)
        - match_confidence (float)
        - gap_status (str)
    """
    columns = [
        "skill",
        "demand_count",
        "matched_course",
        "match_confidence",
        "gap_status",
    ]

    if demand_df is None or demand_df.empty:
        return pd.DataFrame(columns=columns)

    if curriculum_df is None or curriculum_df.empty:
        results = []
        for _, row in demand_df.iterrows():
            results.append(
                {
                    "skill": str(row.get("skill", "")),
                    "demand_count": int(row.get("demand_count", 0)),
                    "matched_course": "None",
                    "match_confidence": 0.0,
                    "gap_status": "missing",
                }
            )
        return pd.DataFrame(results)[columns]

    # Pre-process curriculum items
    courses = []
    for _, c_row in curriculum_df.iterrows():
        c_id = c_row.get("course_id", "")
        c_name = str(c_row.get("course_name", "")).strip()
        c_sector = str(c_row.get("sector", "")).strip()
        skills_raw = str(c_row.get("skills_taught", "")).strip()

        taught_list = [
            s.strip() for s in skills_raw.split(",") if s.strip() and s.strip() != "nan"
        ]

        courses.append(
            {
                "course_id": c_id,
                "course_name": c_name,
                "sector": c_sector,
                "skills_taught": taught_list,
            }
        )

    results = []

    for _, d_row in demand_df.iterrows():
        skill = str(d_row.get("skill", "")).strip()
        demand_count = int(d_row.get("demand_count", 0))

        if not skill:
            continue

        skill_lower = skill.lower()
        best_score = 0.0
        best_course_name = "None"

        # Search across all courses
        for course in courses:
            course_name = course["course_name"]
            taught_skills = course["skills_taught"]

            # Compute partial_ratio against each taught skill
            for taught in taught_skills:
                score = float(fuzz.partial_ratio(skill_lower, taught.lower()))
                if score > best_score:
                    best_score = score
                    best_course_name = course_name

            # Also check against course name
            if course_name:
                name_score = float(fuzz.partial_ratio(skill_lower, course_name.lower()))
                if name_score > best_score:
                    best_score = name_score
                    best_course_name = course_name

        gap_status = get_gap_status(best_score)
        match_confidence = round(best_score, 1)

        matched_course = best_course_name if best_score >= 50.0 else "None"

        results.append(
            {
                "skill": skill,
                "demand_count": demand_count,
                "matched_course": matched_course,
                "match_confidence": match_confidence,
                "gap_status": gap_status,
            }
        )

    result_df = pd.DataFrame(results)

    # Sort: missing and partial gaps with highest demand first, then covered
    status_order = {"missing": 0, "partial": 1, "covered": 2}
    result_df["_sort_order"] = result_df["gap_status"].map(status_order)
    result_df = result_df.sort_values(
        by=["_sort_order", "demand_count", "match_confidence", "skill"],
        ascending=[True, False, False, True],
    ).drop(columns=["_sort_order"]).reset_index(drop=True)

    return result_df[columns]


def main():
    from src.load_data import load_all_data
    from src.demand_scorer import compute_demand

    print("=== Testing Skill Gap Detector ===")
    jobs_df, curriculum_df = load_all_data()
    demand_df = compute_demand(jobs_df)
    gap_df = detect_gaps(demand_df, curriculum_df)

    print(f"\nTotal Analyzed Skills: {len(gap_df)}")
    print("\nGap Status Distribution:")
    print(gap_df["gap_status"].value_counts().to_string())

    print("\n=== SKILL GAP ANALYSIS RESULTS (First 25 Skills) ===")
    print("=" * 110)
    print(
        f"{'SKILL':<36} | {'DEMAND':<6} | {'GAP STATUS':<10} | {'CONFIDENCE':<10} | {'MATCHED COURSE'}"
    )
    print("=" * 110)

    for _, row in gap_df.head(25).iterrows():
        print(
            f"{row['skill']:<36} | {row['demand_count']:<6} | {row['gap_status']:<10} | "
            f"{row['match_confidence']:<10.1f} | {row['matched_course']}"
        )
    print("=" * 110)


if __name__ == "__main__":
    main()
