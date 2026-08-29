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


def compute_skill_similarity(skill: str, candidate: str) -> float:
    """
    Computes similarity between an in-demand skill and a curriculum course skill.
    Accurately matches compound vocational skills (e.g. 'Python' -> 'Python programming',
    'CAN Bus' -> 'CAN Bus Diagnostics') while correctly classifying unmatched skills (<50%) as missing gaps.
    """
    s1 = skill.strip().lower()
    s2 = candidate.strip().lower()

    if not s1 or not s2:
        return 0.0

    # Exact match or complete substring containment is 100%
    if s1 == s2 or s1 in s2 or s2 in s1:
        return 100.0

    w1 = set(s1.split())
    w2 = set(s2.split())

    # If phrases share actual words in common
    if w1.intersection(w2):
        return float(fuzz.token_set_ratio(s1, s2))

    # Single-word comparison (e.g. slight typos or spelling variations)
    if len(w1) == 1 and len(w2) == 1:
        return float(fuzz.ratio(s1, s2))

    # High-confidence partial match
    p_score = float(fuzz.partial_ratio(s1, s2))
    if p_score >= 85.0:
        return p_score

    # Full string ratio for unrelated multi-word phrases
    return float(fuzz.ratio(s1, s2))


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

        best_score = 0.0
        best_course_name = "None"

        # Match against taught skills across all curriculum courses
        for course in courses:
            course_name = course["course_name"]
            taught_skills = course["skills_taught"]

            for taught in taught_skills:
                score = compute_skill_similarity(skill, taught)
                if score > best_score:
                    best_score = score
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


def flag_trainer_needs(gap_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    """
    Identifies trainer upskilling needs based on detected curriculum gaps.
    Filters for skills marked as 'missing' or 'partial' and generates actionable reasons.

    Args:
        gap_df: DataFrame output from detect_gaps() containing:
                ['skill', 'demand_count', 'matched_course', 'match_confidence', 'gap_status']

    Returns:
        DataFrame with columns:
        - skill (str): In-demand skill needing trainer capability
        - demand_count (int): Frequency of market demand
        - trainer_upskilling_needed (bool): True if faculty development is required
        - reason (str): Contextual rationale for trainer development
    """
    columns = [
        "skill",
        "demand_count",
        "trainer_upskilling_needed",
        "reason",
    ]

    if gap_df is None or gap_df.empty:
        return pd.DataFrame(columns=columns)

    # Filter for skills that are either missing or only partially covered
    needs_df = gap_df[gap_df["gap_status"].isin(["missing", "partial"])].copy()

    if needs_df.empty:
        return pd.DataFrame(columns=columns)

    records = []
    for _, row in needs_df.iterrows():
        skill = str(row["skill"])
        demand_count = int(row.get("demand_count", 0))
        gap_status = str(row.get("gap_status", "")).lower()
        matched_course = str(row.get("matched_course", "None"))
        confidence = float(row.get("match_confidence", 0.0))

        if gap_status == "missing":
            trainer_needed = True
            reason = (
                f"Critical Gap: '{skill}' is actively demanded by industry (count: {demand_count}) "
                f"but has 0% coverage across vocational curricula. New master trainer certification required."
            )
        elif gap_status == "partial":
            trainer_needed = True
            if demand_count >= 2:
                reason = (
                    f"High Priority: '{skill}' has strong demand (count: {demand_count}) with only "
                    f"partial curriculum alignment ({confidence}% match with '{matched_course}'). "
                    f"Trainers must be upskilled to bridge modern industry standards."
                )
            else:
                reason = (
                    f"Emerging Demand: '{skill}' shows partial alignment ({confidence}% match with '{matched_course}'). "
                    f"Vocational instructor workshops recommended."
                )
        else:
            trainer_needed = False
            reason = "Skill is adequately covered in existing course curriculum."

        records.append(
            {
                "skill": skill,
                "demand_count": demand_count,
                "trainer_upskilling_needed": trainer_needed,
                "reason": reason,
            }
        )

    trainer_df = pd.DataFrame(records)
    trainer_df = trainer_df.sort_values(
        by=["demand_count", "skill"], ascending=[False, True]
    ).reset_index(drop=True)

    return trainer_df[columns]


def main():
    from src.load_data import load_all_data
    from src.demand_scorer import compute_demand

    print("=== Testing Skill Gap Detector & Trainer Needs ===")
    jobs_df, curriculum_df = load_all_data()
    demand_df = compute_demand(jobs_df)
    gap_df = detect_gaps(demand_df, curriculum_df)
    trainer_df = flag_trainer_needs(gap_df)

    print(f"\nTotal Analyzed Skills: {len(gap_df)}")
    print(f"Total Skills Requiring Trainer Upskilling: {len(trainer_df)}")

    print("\n=== TOP TRAINER DEVELOPMENT PRIORITIES ===")
    print("=" * 115)
    print(
        f"{'SKILL':<32} | {'DEMAND':<6} | {'UPSKILL?':<8} | {'REASON'}"
    )
    print("=" * 115)

    for _, row in trainer_df.head(15).iterrows():
        print(
            f"{row['skill']:<32} | {row['demand_count']:<6} | {str(row['trainer_upskilling_needed']):<8} | {row['reason']}"
        )
    print("=" * 115)


if __name__ == "__main__":
    main()
