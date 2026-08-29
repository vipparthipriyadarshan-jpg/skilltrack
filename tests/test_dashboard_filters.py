import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.load_data import load_all_data
from src.demand_scorer import compute_demand
from src.gap_detector import detect_gaps, flag_trainer_needs


def test_filters_and_styling():
    print("=== Testing Dashboard Filter Combinations & Table Styling ===")
    jobs_df, curr_df = load_all_data()
    assert jobs_df is not None and curr_df is not None
    
    demand_df = compute_demand(jobs_df)
    gap_df = detect_gaps(demand_df, curr_df)
    trainer_df = flag_trainer_needs(gap_df)
    
    all_sectors = sorted(jobs_df["sector"].dropna().unique().tolist())
    all_districts = sorted(jobs_df["district"].dropna().unique().tolist())
    
    print(f"Loaded {len(jobs_df)} jobs, {len(curr_df)} courses, {len(demand_df)} skills.")
    
    # 1. Test Sector Filtering
    for sec in all_sectors:
        mask = demand_df.apply(
            lambda r: sec in r["sectors"],
            axis=1,
        )
        f_dem = demand_df[mask]
        f_gap = detect_gaps(f_dem, curr_df)
        print(f"Sector Filter [{sec}]: {len(f_dem)} skills, {len(f_gap)} gap entries -> OK")
        assert len(f_dem) > 0
    
    # 2. Test District Filtering
    for dist in all_districts:
        mask = demand_df.apply(
            lambda r: dist in r["districts"],
            axis=1,
        )
        f_dem = demand_df[mask]
        f_gap = detect_gaps(f_dem, curr_df)
        print(f"District Filter [{dist}]: {len(f_dem)} skills, {len(f_gap)} gap entries -> OK")
        assert len(f_dem) > 0
        
    # 3. Test Gap Status Filtering
    for status in ["covered", "partial", "missing"]:
        subset = gap_df[gap_df["gap_status"] == status]
        print(f"Status Filter [{status}]: {len(subset)} entries -> OK")

    # 4. Test Course Health Audit Calculation and Styler
    demanded_lower = set(demand_df["skill"].str.lower().tolist())
    records = []
    for _, cr in curr_df.iterrows():
        taught = [s.strip() for s in str(cr.get("skills_taught", "")).split(",") if s.strip()]
        total = len(taught)
        cov = [s for s in taught if s.lower() in demanded_lower]
        gaps = [s for s in taught if s.lower() not in demanded_lower]
        pct = round(len(cov) / total * 100, 1) if total else 0
        if pct >= 70:
            health = "🟢 Aligned"
        elif pct >= 40:
            health = "🟡 Needs Update"
        else:
            health = "🔴 Obsolete"
        records.append({
            "Course ID": cr["course_id"], "Course Name": cr["course_name"],
            "Sector": cr.get("sector", ""), "Total Skills": total,
            "Demanded Skills": len(cov), "Coverage %": pct,
            "Health": health, "Gap Skills": ", ".join(gaps),
        })
    ch_df = pd.DataFrame(records)
    
    def color_health(row):
        h = str(row["Health"])
        if "Aligned" in h:
            return ["background-color:rgba(16,185,129,0.07);color:#34D399"] * len(row)
        elif "Update" in h:
            return ["background-color:rgba(245,158,11,0.07);color:#FBBF24"] * len(row)
        return ["background-color:rgba(239,68,68,0.07);color:#F87171"] * len(row)

    styled_ch = ch_df.style.apply(color_health, axis=1).format({"Coverage %": "{:.1f}%"})
    # Render HTML from Styler to ensure computation has zero errors
    html_output = styled_ch.to_html()
    assert len(html_output) > 100
    print("Course Health Styler test passed with zero errors -> OK")
    
    # 5. Test Gap Styler
    def color_gap(row):
        s = row["gap_status"]
        if s == "covered":
            return ["background-color:rgba(16,185,129,0.07);color:#34D399"] * len(row)
        elif s == "partial":
            return ["background-color:rgba(245,158,11,0.07);color:#FBBF24"] * len(row)
        return ["background-color:rgba(239,68,68,0.07);color:#F87171"] * len(row)

    styled_gap = gap_df.style.apply(color_gap, axis=1).format({"match_confidence": "{:.1f}%"})
    gap_html = styled_gap.to_html()
    assert len(gap_html) > 100
    print("Gap Styler test passed with zero errors -> OK")

    print("\nALL FILTER AND STYLING TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_filters_and_styling()
