import os
import sys
from pathlib import Path
from typing import Dict, List
import pandas as pd
import streamlit as st

# Ensure repository root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.load_data import load_all_data
from src.skill_extractor import extract_skills, SKILL_KEYWORDS
from src.demand_scorer import compute_demand
from src.gap_detector import detect_gaps, flag_trainer_needs

# -----------------------------------------------------------------------------
# Streamlit Page Configuration (Modern Wide Layout)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="SkillTrack AI • Vocational Skill Alignment Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Design Engineering CSS (Emil Kowalski Craft & Apple Fluid Design Inspired)
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
        --radius-sm: 8px;
        --radius-md: 14px;
        --radius-lg: 20px;
        --radius-full: 9999px;
        --transition-spring: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    * {
        font-family: var(--font-sans) !important;
    }

    code, pre, .stCode {
        font-family: var(--font-mono) !important;
    }

    /* Main container refinements */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1380px !important;
    }

    /* Top Glass Header Card */
    .hero-container {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: var(--radius-lg);
        padding: 2.2rem 2.5rem;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.3);
        position: relative;
        overflow: hidden;
    }

    .hero-container::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -20%;
        width: 380px;
        height: 380px;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.25) 0%, rgba(168, 85, 247, 0.1) 50%, transparent 70%);
        pointer-events: none;
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #FFFFFF;
        margin: 0 0 0.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }

    .hero-subtitle {
        font-size: 1.05rem;
        color: #94A3B8;
        margin: 0;
        max-width: 820px;
        line-height: 1.6;
    }

    /* Metric / KPI Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1.25rem;
        margin-bottom: 2rem;
    }

    .kpi-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(12px);
        border-radius: var(--radius-md);
        padding: 1.4rem 1.6rem;
        transition: var(--transition-spring);
        position: relative;
    }

    .kpi-card:hover {
        transform: translateY(-3px);
        border-color: rgba(99, 102, 241, 0.4);
        box-shadow: 0 12px 24px -10px rgba(99, 102, 241, 0.2);
    }

    .kpi-label {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #94A3B8;
        margin-bottom: 0.4rem;
    }

    .kpi-value {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #F8FAFC;
    }

    .kpi-subtext {
        font-size: 0.8rem;
        color: #64748B;
        margin-top: 0.35rem;
    }

    /* Status Pill Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.28rem 0.75rem;
        border-radius: var(--radius-full);
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .badge-covered {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .badge-partial {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .badge-missing {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    .badge-sector {
        background: rgba(99, 102, 241, 0.15);
        color: #818CF8;
        border: 1px solid rgba(99, 102, 241, 0.25);
    }

    /* Section Header Card */
    .section-header {
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: baseline;
        justify-content: space-between;
    }

    .section-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #F1F5F9;
        letter-spacing: -0.02em;
    }

    .section-desc {
        font-size: 0.9rem;
        color: #94A3B8;
    }

    /* Interactive Simulator Card */
    .sim-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: var(--radius-md);
        padding: 1.6rem;
        margin-top: 1rem;
    }

    /* Tab styling override */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 42px;
        padding: 0 1.25rem;
        border-radius: var(--radius-sm);
        font-weight: 600;
        font-size: 0.9rem;
        transition: var(--transition-spring);
    }

    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.2) !important;
        color: #818CF8 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def get_cached_pipeline_data():
    """
    Loads raw datasets, extracts skills, computes demand, and calculates gap & trainer insights.
    """
    jobs_df, curr_df = load_all_data()
    if jobs_df is None or curr_df is None:
        return None, None, None, None, None

    # Compute skill demand
    demand_df = compute_demand(jobs_df)

    # Detect curriculum gaps
    gap_df = detect_gaps(demand_df, curr_df)

    # Flag trainer upskilling needs
    trainer_df = flag_trainer_needs(gap_df)

    return jobs_df, curr_df, demand_df, gap_df, trainer_df


def render_header():
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-title">
                <span>⚡ SkillTrack AI</span>
                <span class="badge badge-sector" style="font-size:0.75rem;">Maharashtra Skill Ecosystem</span>
            </div>
            <p class="hero-subtitle">
                Intelligent vocational alignment engine matching real-time industry job demand against vocational curricula across 
                <strong>Pune, Nashik, and Nagpur</strong>. Identifies missing market competencies and generates actionable trainer development roadmaps.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_dashboard(jobs_df, curr_df, gap_df, trainer_df):
    total_jobs = len(jobs_df)
    total_courses = len(curr_df)
    total_skills = len(gap_df)
    
    covered_count = len(gap_df[gap_df["gap_status"] == "covered"])
    partial_count = len(gap_df[gap_df["gap_status"] == "partial"])
    missing_count = len(gap_df[gap_df["gap_status"] == "missing"])
    
    coverage_rate = (covered_count / total_skills * 100) if total_skills else 0
    trainer_priority_count = len(trainer_df)

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Market Jobs Analyzed</div>
                <div class="kpi-value">{total_jobs}</div>
                <div class="kpi-subtext">Across IT, Auto, Textile</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Vocational Courses</div>
                <div class="kpi-value">{total_courses}</div>
                <div class="kpi-subtext">Curricula Benchmarked</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Unique Skills Tracked</div>
                <div class="kpi-value">{total_skills}</div>
                <div class="kpi-subtext">Extracted via spaCy NLP</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">Curriculum Alignment</div>
                <div class="kpi-value">{coverage_rate:.1f}%</div>
                <div class="kpi-subtext">{covered_count} Covered • {partial_count} Partial</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            f"""
            <div class="kpi-card" style="border-color: rgba(239, 68, 68, 0.3);">
                <div class="kpi-label" style="color: #F87171;">Trainer Upskill Priority</div>
                <div class="kpi-value" style="color: #F87171;">{trainer_priority_count}</div>
                <div class="kpi-subtext">Urgent Faculty Interventions</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main():
    jobs_df, curr_df, demand_df, gap_df, trainer_df = get_cached_pipeline_data()

    if jobs_df is None:
        st.error("Failed to load sample datasets. Please ensure data/jobs_sample.csv and data/curriculum_sample.csv exist.")
        return

    # Render Header & KPIs
    render_header()
    render_kpi_dashboard(jobs_df, curr_df, gap_df, trainer_df)

    # -------------------------------------------------------------------------
    # Navigation Tabs
    # -------------------------------------------------------------------------
    tabs = st.tabs([
        "🔍 Skill Gap Matrix",
        "👨‍🏫 Trainer Development Planner",
        "📊 Sector & Regional Intelligence",
        "🧪 Interactive AI Playground",
        "📁 Raw Data Explorer",
    ])

    # -------------------------------------------------------------------------
    # TAB 1: Skill Gap Matrix
    # -------------------------------------------------------------------------
    with tabs[0]:
        st.markdown(
            """
            <div class="section-header">
                <div>
                    <div class="section-title">Curriculum Alignment & Gap Matrix</div>
                    <div class="section-desc">Fuzzy matching between live job requirements and vocational training programs (rapidfuzz partial_ratio >= 80% threshold).</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Filters Bar
        f_col1, f_col2, f_col3 = st.columns([2, 2, 3])
        with f_col1:
            status_filter = st.multiselect(
                "Filter by Gap Status",
                options=["covered", "partial", "missing"],
                default=["partial", "covered"],
            )
        with f_col2:
            min_demand = st.slider("Minimum Job Demand Count", min_value=1, max_value=int(demand_df["demand_count"].max()), value=1)
        with f_col3:
            search_query = st.text_input("Search Specific Skill or Course", placeholder="e.g., Docker, Python, Battery, Weaving...")

        # Apply Filters
        filtered_gap = gap_df.copy()
        if status_filter:
            filtered_gap = filtered_gap[filtered_gap["gap_status"].isin(status_filter)]
        filtered_gap = filtered_gap[filtered_gap["demand_count"] >= min_demand]

        if search_query:
            q = search_query.strip().lower()
            filtered_gap = filtered_gap[
                filtered_gap["skill"].str.lower().str.contains(q)
                | filtered_gap["matched_course"].str.lower().str.contains(q)
            ]

        st.caption(f"Showing {len(filtered_gap)} skill entries matching criteria.")

        # Interactive Table Display
        display_df = filtered_gap.copy()
        
        # Color formatted dataframe
        st.dataframe(
            display_df,
            column_config={
                "skill": st.column_config.TextColumn("In-Demand Skill", width="medium"),
                "demand_count": st.column_config.NumberColumn("Demand Count", format="%d", width="small"),
                "gap_status": st.column_config.TextColumn("Gap Status", width="small"),
                "match_confidence": st.column_config.ProgressColumn("Match Confidence", min_value=0, max_value=100, format="%.1f%%"),
                "matched_course": st.column_config.TextColumn("Best Matched Course", width="large"),
            },
            use_container_width=True,
            hide_index=True,
        )

        # Download Button
        csv_data = filtered_gap.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Gap Matrix CSV",
            data=csv_data,
            file_name="skill_gap_matrix_report.csv",
            mime="text/csv",
        )

    # -------------------------------------------------------------------------
    # TAB 2: Trainer Development Planner
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.markdown(
            """
            <div class="section-header">
                <div>
                    <div class="section-title">Trainer Development & Faculty Upskilling Roadmap</div>
                    <div class="section-desc">Actionable intervention recommendations for ITI/vocational faculty to align teaching with emerging industrial demands.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.info(
                "💡 **Strategic Policy Insight**: Bridging skill gaps requires equipping vocational instructors "
                "before rolling out curriculum updates. The interventions below highlight priority technologies missing in current syllabi."
            )
        with col_t2:
            st.metric("Total Faculty Interventions", len(trainer_df), delta=f"{len(trainer_df[trainer_df['demand_count'] >= 2])} High Demand", delta_color="inverse")

        st.dataframe(
            trainer_df,
            column_config={
                "skill": st.column_config.TextColumn("Emerging Skill / Technology", width="medium"),
                "demand_count": st.column_config.NumberColumn("Market Demand", format="%d", width="small"),
                "trainer_upskilling_needed": st.column_config.CheckboxColumn("Faculty Action Required", width="small"),
                "reason": st.column_config.TextColumn("Strategic Upskilling Rationale & Action Plan", width="large"),
            },
            use_container_width=True,
            hide_index=True,
        )

        trainer_csv = trainer_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Trainer Roadmap CSV",
            data=trainer_csv,
            file_name="trainer_development_roadmap.csv",
            mime="text/csv",
        )

    # -------------------------------------------------------------------------
    # TAB 3: Sector & Regional Intelligence
    # -------------------------------------------------------------------------
    with tabs[2]:
        st.markdown(
            """
            <div class="section-header">
                <div>
                    <div class="section-title">Sectoral & Regional Distribution</div>
                    <div class="section-desc">Breakdown of market hiring demand and skill clusters across Pune, Nashik, and Nagpur.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.subheader("Jobs Distribution by Sector")
            sector_counts = jobs_df["sector"].value_counts().reset_index()
            sector_counts.columns = ["Sector", "Job Postings"]
            st.bar_chart(sector_counts.set_index("Sector"), color="#6366F1")

        with col_s2:
            st.subheader("Jobs Distribution by District")
            district_counts = jobs_df["district"].value_counts().reset_index()
            district_counts.columns = ["District", "Job Postings"]
            st.bar_chart(district_counts.set_index("District"), color="#A855F7")

        st.subheader("Top Demanded Skills with Regional Footprint")
        st.dataframe(
            demand_df.head(15),
            column_config={
                "skill": st.column_config.TextColumn("Skill"),
                "demand_count": st.column_config.NumberColumn("Demand Count"),
                "sectors": st.column_config.ListColumn("Sectors"),
                "districts": st.column_config.ListColumn("Districts"),
            },
            use_container_width=True,
            hide_index=True,
        )

    # -------------------------------------------------------------------------
    # TAB 4: Interactive AI Playground
    # -------------------------------------------------------------------------
    with tabs[3]:
        st.markdown(
            """
            <div class="section-header">
                <div>
                    <div class="section-title">Live spaCy Skill Extractor & Real-Time Gap Tester</div>
                    <div class="section-desc">Paste any arbitrary job description or vocational syllabus text to test real-time NLP extraction and benchmark against vocational courses.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sample_inputs = [
            "We are hiring a Senior Cloud Architect proficient in Docker, Kubernetes, Terraform, and AWS Cloud with microservices architecture experience.",
            "Urgent opening for Electric Vehicle Powertrain Specialist with CAN Bus Diagnostics, MATLAB Simulink, and Battery Chemistry expertise in Pune.",
            "Seeking Master Weaver with deep knowledge of Digital Textile Printing, Sublimation Printing, and Shade Matching in Nagpur.",
        ]

        preset = st.selectbox("Select an Example Job Requirement or type custom text below:", ["(Custom Text)"] + sample_inputs)
        
        default_val = "" if preset == "(Custom Text)" else preset
        user_text = st.text_area(
            "Enter Job Posting Description or Course Syllabus:",
            value=default_val,
            height=130,
            placeholder="e.g. Looking for a Data Scientist with Python, PyTorch, LangChain, Vector Databases, and Scikit-Learn skills...",
        )

        if st.button("🚀 Analyze Text & Detect Gaps", type="primary"):
            if not user_text.strip():
                st.warning("Please enter some text to analyze.")
            else:
                with st.spinner("Extracting skills with spaCy NLP pipeline..."):
                    extracted = extract_skills(user_text)

                if not extracted:
                    st.warning("No canonical skills from the catalog were detected in the provided text.")
                else:
                    st.success(f"Extracted {len(extracted)} skills successfully!")

                    # Build mini demand dataframe
                    mini_demand = pd.DataFrame([{"skill": s, "demand_count": 1} for s in extracted])
                    mini_gap = detect_gaps(mini_demand, curr_df)
                    mini_trainer = flag_trainer_needs(mini_gap)

                    c_res1, c_res2 = st.columns([3, 2])

                    with c_res1:
                        st.markdown("#### Real-Time Gap Analysis")
                        st.dataframe(
                            mini_gap,
                            column_config={
                                "skill": st.column_config.TextColumn("Extracted Skill"),
                                "demand_count": st.column_config.NumberColumn("Count"),
                                "gap_status": st.column_config.TextColumn("Status"),
                                "match_confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100, format="%.1f%%"),
                                "matched_course": st.column_config.TextColumn("Best Matched Course"),
                            },
                            use_container_width=True,
                            hide_index=True,
                        )

                    with c_res2:
                        st.markdown("#### Trainer Upskilling Advisory")
                        if mini_trainer.empty:
                            st.info("All extracted skills are adequately covered in existing curricula!")
                        else:
                            for _, r in mini_trainer.iterrows():
                                st.markdown(
                                    f"""
                                    <div style="background:rgba(255,255,255,0.04); border-left:3px solid #F59E0B; padding:0.75rem 1rem; border-radius:6px; margin-bottom:0.5rem;">
                                        <strong>{r['skill']}</strong><br/>
                                        <span style="font-size:0.85rem; color:#CBD5E1;">{r['reason']}</span>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

    # -------------------------------------------------------------------------
    # TAB 5: Raw Data Explorer
    # -------------------------------------------------------------------------
    with tabs[4]:
        st.markdown(
            """
            <div class="section-header">
                <div>
                    <div class="section-title">Raw Benchmark Data Explorer</div>
                    <div class="section-desc">Explore the underlying industry job postings and vocational curriculum dataset records.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.markdown(f"#### Industry Job Postings ({len(jobs_df)} records)")
            st.dataframe(jobs_df, use_container_width=True, hide_index=True)
        with d_col2:
            st.markdown(f"#### Vocational Courses Curriculum ({len(curr_df)} records)")
            st.dataframe(curr_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
