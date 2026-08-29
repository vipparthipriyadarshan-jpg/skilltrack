"""
Skill-Industry Alignment Dashboard — PS 26134
================================================
Production-grade Streamlit dashboard blending Emil Kowalski's design
engineering philosophy (invisible polish, spring-based transitions,
Apple-inspired depth) with the full NLP analysis pipeline.

Run with:
    streamlit run app/dashboard.py
"""

import sys
from pathlib import Path
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Resolve project root so `src.*` imports work regardless of working dir.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.load_data import load_all_data
from src.skill_extractor import extract_skills
from src.demand_scorer import compute_demand
from src.gap_detector import detect_gaps, flag_trainer_needs

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PAGE CONFIG — must be the first Streamlit command                       ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
st.set_page_config(
    page_title="Skill-Industry Alignment Dashboard — PS 26134",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  DESIGN SYSTEM — Emil Kowalski craft + Apple fluid aesthetic             ║
# ║                                                                          ║
# ║  Principles applied:                                                     ║
# ║  • Taste is trained — every detail compounds into "feels right"          ║
# ║  • Spring curves for hover (cubic-bezier 0.16,1,0.3,1)                  ║
# ║  • Optical balance via letter-spacing & font-weight hierarchy            ║
# ║  • Translucent depth layers, never flat                                  ║
# ║  • Restraint — animate only what earns it                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
DESIGN_CSS = """
<style>
/* ── Fonts ───────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', monospace;

    /* ── Radii (Apple-rounded) ──────────────────────────────────────────── */
    --r-xs: 6px;
    --r-sm: 10px;
    --r-md: 14px;
    --r-lg: 20px;
    --r-pill: 9999px;

    /* ── Spring transition ──────────────────────────────────────────────── */
    --spring: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);

    /* ── Palette ────────────────────────────────────────────────────────── */
    --bg-surface: rgba(15, 23, 42, 0.92);
    --bg-card: rgba(30, 41, 59, 0.55);
    --bg-card-hover: rgba(30, 41, 59, 0.75);
    --border-subtle: rgba(255, 255, 255, 0.08);
    --border-hover: rgba(99, 102, 241, 0.45);
    --text-primary: #F1F5F9;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    --accent: #6366F1;
    --accent-glow: rgba(99, 102, 241, 0.22);
    --green: #34D399;
    --green-bg: rgba(16, 185, 129, 0.12);
    --green-border: rgba(16, 185, 129, 0.35);
    --amber: #FBBF24;
    --amber-bg: rgba(245, 158, 11, 0.12);
    --amber-border: rgba(245, 158, 11, 0.35);
    --red: #F87171;
    --red-bg: rgba(239, 68, 68, 0.12);
    --red-border: rgba(239, 68, 68, 0.35);
}

* { font-family: var(--font-sans) !important; }
code, pre, .stCode { font-family: var(--font-mono) !important; }

/* ── Layout ──────────────────────────────────────────────────────────────── */
.block-container {
    padding-top: 1.6rem !important;
    padding-bottom: 4rem !important;
    max-width: 1400px !important;
}

/* ── Hero Header ─────────────────────────────────────────────────────────── */
.dash-hero {
    background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(30,41,59,0.95) 100%);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-lg);
    padding: 2rem 2.4rem 1.8rem;
    margin-bottom: 1.8rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 24px 48px -16px rgba(0,0,0,0.35);
}

.dash-hero::after {
    content: "";
    position: absolute;
    top: -60%;
    right: -14%;
    width: 420px;
    height: 420px;
    background: radial-gradient(circle, var(--accent-glow) 0%, rgba(168,85,247,0.08) 55%, transparent 72%);
    pointer-events: none;
}

.dash-hero h1 {
    font-size: 1.95rem;
    font-weight: 800;
    letter-spacing: -0.035em;
    color: #FFF;
    margin: 0 0 0.35rem;
    line-height: 1.2;
}

.dash-hero .ps-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0.22rem 0.7rem;
    border-radius: var(--r-pill);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: var(--accent-glow);
    color: #A5B4FC;
    border: 1px solid rgba(99,102,241,0.3);
    margin-left: 0.8rem;
    vertical-align: middle;
}

.dash-hero p {
    font-size: 0.97rem;
    color: var(--text-secondary);
    margin: 0.55rem 0 0;
    max-width: 860px;
    line-height: 1.65;
}

/* ── KPI Cards ───────────────────────────────────────────────────────────── */
.kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(195px,1fr)); gap: 1rem; margin-bottom: 1.6rem; }

.kpi {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: 1.15rem 1.3rem;
    transition: var(--spring);
    backdrop-filter: blur(10px);
}
.kpi:hover { transform: translateY(-2px); border-color: var(--border-hover); box-shadow: 0 10px 22px -8px var(--accent-glow); }

.kpi-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-muted); margin-bottom: 0.25rem; }
.kpi-value { font-size: 1.85rem; font-weight: 800; letter-spacing: -0.04em; color: var(--text-primary); }
.kpi-sub   { font-size: 0.73rem; color: var(--text-muted); margin-top: 0.2rem; }

/* ── Section Headers ─────────────────────────────────────────────────────── */
.sec-head { margin: 1.5rem 0 0.8rem; }
.sec-title { font-size: 1.2rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
.sec-desc  { font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.15rem; }

/* ── Status Pills ────────────────────────────────────────────────────────── */
.pill { display:inline-flex; align-items:center; gap:5px; padding:0.2rem 0.65rem; border-radius:var(--r-pill); font-size:0.7rem; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; }
.pill-covered { background:var(--green-bg); color:var(--green); border:1px solid var(--green-border); }
.pill-partial { background:var(--amber-bg); color:var(--amber); border:1px solid var(--amber-border); }
.pill-missing { background:var(--red-bg);   color:var(--red);   border:1px solid var(--red-border); }

/* ── Sidebar polish ──────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: rgba(15,23,42,0.97) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

section[data-testid="stSidebar"] .stMarkdown h3 {
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-muted);
    margin-top: 1rem;
}

/* ── Trainer card ────────────────────────────────────────────────────────── */
.trainer-card {
    background: var(--bg-card);
    border-left: 3px solid var(--amber);
    border-radius: 0 var(--r-sm) var(--r-sm) 0;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.6rem;
    transition: var(--spring);
}
.trainer-card:hover { background: var(--bg-card-hover); transform: translateX(3px); }
.trainer-card strong { color: var(--text-primary); font-size: 0.92rem; }
.trainer-card .reason { color: var(--text-secondary); font-size: 0.82rem; line-height: 1.55; margin-top: 0.25rem; }

/* ── Error state ─────────────────────────────────────────────────────────── */
.friendly-error {
    text-align: center;
    padding: 3.5rem 2rem;
    background: var(--bg-card);
    border: 1px dashed rgba(239,68,68,0.4);
    border-radius: var(--r-lg);
    margin: 3rem auto;
    max-width: 620px;
}
.friendly-error .icon { font-size: 3rem; margin-bottom: 0.8rem; }
.friendly-error h2 { color: var(--red); font-size: 1.25rem; font-weight: 700; margin: 0 0 0.5rem; }
.friendly-error p  { color: var(--text-secondary); font-size: 0.92rem; line-height: 1.6; }

/* ── Course Health Cards ─────────────────────────────────────────────────── */
.course-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: var(--r-md);
    padding: 1rem 1.2rem;
    margin-bottom: 0.7rem;
    transition: var(--spring);
    display: flex;
    align-items: flex-start;
    gap: 1rem;
}
.course-card:hover { background: var(--bg-card-hover); transform: translateY(-1px); box-shadow: 0 6px 16px -6px rgba(0,0,0,0.2); }
.course-card .badge-icon { font-size: 1.6rem; flex-shrink: 0; margin-top: 2px; }
.course-card .course-info { flex: 1; }
.course-card .course-name { font-size: 0.95rem; font-weight: 700; color: var(--text-primary); }
.course-card .course-sector { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; }
.course-card .course-skills { font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.35rem; line-height: 1.5; }
.course-card .health-badge { flex-shrink: 0; margin-top: 2px; }

/* ── Trainer Alert Panel ─────────────────────────────────────────────────── */
.trainer-panel {
    background: linear-gradient(135deg, rgba(239,68,68,0.06) 0%, rgba(245,158,11,0.06) 100%);
    border: 1px solid rgba(245,158,11,0.25);
    border-radius: var(--r-lg);
    padding: 1.4rem 1.6rem;
    margin: 1.2rem 0 1.8rem;
}
.trainer-panel .panel-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 0.8rem;
}
.trainer-panel .panel-title { font-size: 1.1rem; font-weight: 700; color: var(--text-primary); }
.trainer-panel .panel-count { font-size: 0.72rem; font-weight: 700; padding: 0.15rem 0.55rem; border-radius: var(--r-pill); background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }
.trainer-chip-grid { display: flex; flex-wrap: wrap; gap: 0.45rem; }
.trainer-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 0.3rem 0.75rem;
    border-radius: var(--r-pill);
    font-size: 0.78rem;
    font-weight: 600;
    transition: var(--spring);
    cursor: default;
}
.trainer-chip:hover { transform: translateY(-1px); }
.trainer-chip-high { background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }
.trainer-chip-med  { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
</style>
"""

st.markdown(DESIGN_CSS, unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  DATA PIPELINE — wrapped in try/except for graceful degradation         ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
@st.cache_data(show_spinner=False)
def run_pipeline():
    """
    Full analysis pipeline: load → extract → score → gap detect → trainer flags.
    Returns a dict of DataFrames or raises on missing files.
    """
    jobs_df, curr_df = load_all_data()

    if jobs_df is None:
        raise FileNotFoundError(
            "Could not load data/jobs_sample.csv — the file is missing or has invalid columns. "
            "Please ensure it exists in the project /data directory with columns: "
            "job_id, job_title, sector, district, job_description."
        )
    if curr_df is None:
        raise FileNotFoundError(
            "Could not load data/curriculum_sample.csv — the file is missing or has invalid columns. "
            "Please ensure it exists in the project /data directory with columns: "
            "course_id, course_name, sector, skills_taught."
        )

    demand_df = compute_demand(jobs_df)
    gap_df = detect_gaps(demand_df, curr_df)
    trainer_df = flag_trainer_needs(gap_df)

    return {
        "jobs": jobs_df,
        "curriculum": curr_df,
        "demand": demand_df,
        "gap": gap_df,
        "trainer": trainer_df,
    }


def show_friendly_error(error_msg: str):
    """Render a polished on-screen error instead of a raw stack trace."""
    st.markdown(
        f"""
        <div class="friendly-error">
            <div class="icon">📂</div>
            <h2>Data Not Available</h2>
            <p>{error_msg}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Attempt pipeline execution ──────────────────────────────────────────────
try:
    data = run_pipeline()
    pipeline_ok = True
except FileNotFoundError as e:
    data = None
    pipeline_ok = False
    pipeline_error = str(e)
except Exception as e:
    data = None
    pipeline_ok = False
    pipeline_error = (
        f"An unexpected error occurred while running the analysis pipeline: {e}. "
        "Check that all required packages are installed and the data files are valid CSV."
    )


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  HERO HEADER                                                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
st.markdown(
    """
    <div class="dash-hero">
        <h1>🎯 Skill-Industry Alignment Dashboard<span class="ps-tag">PS 26134</span></h1>
        <p>
            Real-time NLP-powered intelligence matching <strong>industry job demand</strong>
            against <strong>vocational training curricula</strong> across Maharashtra's
            IT, Automotive, and Textile sectors — surfacing critical skill gaps and
            generating actionable <strong>trainer development roadmaps</strong>.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not pipeline_ok:
    show_friendly_error(pipeline_error)
    st.stop()

# ── Unpack pipeline results ─────────────────────────────────────────────────
jobs_df = data["jobs"]
curr_df = data["curriculum"]
demand_df = data["demand"]
gap_df = data["gap"]
trainer_df = data["trainer"]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  SIDEBAR — Sector & District Filters                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
with st.sidebar:
    st.markdown("### 🏷️ Sector Filter")
    all_sectors = sorted(jobs_df["sector"].dropna().unique().tolist())
    selected_sectors = st.multiselect(
        "Select sectors",
        options=all_sectors,
        default=all_sectors,
        label_visibility="collapsed",
    )

    st.markdown("### 📍 District Filter")
    all_districts = sorted(jobs_df["district"].dropna().unique().tolist())
    selected_districts = st.multiselect(
        "Select districts",
        options=all_districts,
        default=all_districts,
        label_visibility="collapsed",
    )

    st.markdown("### 🚦 Gap Status")
    all_statuses = ["covered", "partial", "missing"]
    selected_statuses = st.multiselect(
        "Filter by alignment status",
        options=all_statuses,
        default=all_statuses,
        label_visibility="collapsed",
    )

    st.markdown("### 🔎 Skill Search")
    skill_query = st.text_input(
        "Search",
        placeholder="e.g. Docker, Battery, Weaving",
        label_visibility="collapsed",
    )

    st.divider()
    st.caption("SkillTrack AI • PS 26134")
    st.caption("NLP Engine: spaCy en_core_web_sm")
    st.caption("Matcher: rapidfuzz partial_ratio ≥ 80")


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  FILTERED DATA — Apply sector/district to demand_df, then re-join       ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

def filter_demand_by_selections(demand_df, selected_sectors, selected_districts):
    """
    Filter the demand DataFrame based on sector and district selections.
    demand_df has 'sectors' and 'districts' columns as lists.
    """
    mask = demand_df.apply(
        lambda row: (
            any(s in selected_sectors for s in row["sectors"])
            and any(d in selected_districts for d in row["districts"])
        ),
        axis=1,
    )
    return demand_df[mask].copy()


filtered_demand = filter_demand_by_selections(demand_df, selected_sectors, selected_districts)
filtered_gap = detect_gaps(filtered_demand, curr_df)
filtered_trainer = flag_trainer_needs(filtered_gap)

# Apply status filter
if selected_statuses:
    display_gap = filtered_gap[filtered_gap["gap_status"].isin(selected_statuses)].copy()
else:
    display_gap = filtered_gap.copy()

# Apply text search
if skill_query.strip():
    q = skill_query.strip().lower()
    display_gap = display_gap[
        display_gap["skill"].str.lower().str.contains(q, na=False)
        | display_gap["matched_course"].str.lower().str.contains(q, na=False)
    ]


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  KPI BAR                                                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

total_skills = len(filtered_gap)
covered = len(filtered_gap[filtered_gap["gap_status"] == "covered"])
partial = len(filtered_gap[filtered_gap["gap_status"] == "partial"])
missing = len(filtered_gap[filtered_gap["gap_status"] == "missing"])
alignment_pct = round(covered / total_skills * 100, 1) if total_skills else 0
trainer_count = len(filtered_trainer)

st.markdown(
    f"""
    <div class="kpi-row">
        <div class="kpi">
            <div class="kpi-label">Jobs Analyzed</div>
            <div class="kpi-value">{len(jobs_df)}</div>
            <div class="kpi-sub">{len(selected_sectors)} sector(s) · {len(selected_districts)} district(s)</div>
        </div>
        <div class="kpi">
            <div class="kpi-label">Skills Tracked</div>
            <div class="kpi-value">{total_skills}</div>
            <div class="kpi-sub">Extracted via spaCy NLP</div>
        </div>
        <div class="kpi">
            <div class="kpi-label" style="color:var(--green)">✓ Covered</div>
            <div class="kpi-value" style="color:var(--green)">{covered}</div>
            <div class="kpi-sub">{alignment_pct}% curriculum alignment</div>
        </div>
        <div class="kpi">
            <div class="kpi-label" style="color:var(--amber)">⚠ Partial</div>
            <div class="kpi-value" style="color:var(--amber)">{partial}</div>
            <div class="kpi-sub">Fuzzy match 50–80%</div>
        </div>
        <div class="kpi">
            <div class="kpi-label" style="color:var(--red)">✕ Missing</div>
            <div class="kpi-value" style="color:var(--red)">{missing}</div>
            <div class="kpi-sub">No curriculum match &lt; 50%</div>
        </div>
        <div class="kpi" style="border-color:var(--red-border)">
            <div class="kpi-label" style="color:var(--red)">Trainer Priority</div>
            <div class="kpi-value" style="color:var(--red)">{trainer_count}</div>
            <div class="kpi-sub">Faculty interventions needed</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  TRAINER UPSKILLING PANEL — always visible on main dashboard             ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

if not filtered_trainer.empty:
    high_chips = filtered_trainer[filtered_trainer["demand_count"] >= 2].sort_values("demand_count", ascending=False)
    emerging_chips = filtered_trainer[filtered_trainer["demand_count"] < 2].sort_values("skill")

    chips_html = ""
    for _, r in high_chips.iterrows():
        chips_html += f'<span class="trainer-chip trainer-chip-high">🔴 {r["skill"]} ({r["demand_count"]})</span>'
    for _, r in emerging_chips.iterrows():
        chips_html += f'<span class="trainer-chip trainer-chip-med">🟡 {r["skill"]}</span>'

    st.markdown(
        f"""
        <div class="trainer-panel">
            <div class="panel-header">
                <span style="font-size:1.3rem">👨‍🏫</span>
                <span class="panel-title">Trainer Upskilling Needed</span>
                <span class="panel-count">{len(filtered_trainer)} skills flagged</span>
            </div>
            <div class="trainer-chip-grid">
                {chips_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  MAIN TABS                                                               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

tab_gap, tab_courses, tab_trainer, tab_explore, tab_playground = st.tabs([
    "🔍  Skill Gap Matrix",
    "🏫  Course Health Audit",
    "👨‍🏫  Trainer Development Planner",
    "📊  Sector & District View",
    "🧪  Live AI Playground",
])


# ── TAB 1: Gap Matrix ───────────────────────────────────────────────────────
with tab_gap:
    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-title">Curriculum Alignment & Gap Matrix</div>
            <div class="sec-desc">
                Color-coded skill alignment using rapidfuzz partial_ratio
                — <span class="pill pill-covered">covered &gt;80%</span>
                <span class="pill pill-partial">partial 50–80%</span>
                <span class="pill pill-missing">missing &lt;50%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Top 10 In-Demand Skills Bar Chart ────────────────────────────────────
    st.markdown("#### Top 10 In-Demand Skills")
    top10 = (
        filtered_demand
        .sort_values("demand_count", ascending=False)
        .head(10)
        .copy()
    )
    if not top10.empty:
        chart_df = top10[["skill", "demand_count"]].set_index("skill")
        st.bar_chart(chart_df, color="#6366F1", height=320)
    else:
        st.info("No demand data available for the current filter selection.")

    st.markdown("")  # spacer

    st.caption(f"Displaying {len(display_gap)} of {len(filtered_gap)} skills after filters.")

    # Color-coded interactive table
    def highlight_gap(row):
        status = row["gap_status"]
        if status == "covered":
            return ["background-color: rgba(16,185,129,0.08); color: #34D399"] * len(row)
        elif status == "partial":
            return ["background-color: rgba(245,158,11,0.08); color: #FBBF24"] * len(row)
        else:
            return ["background-color: rgba(239,68,68,0.08); color: #F87171"] * len(row)

    if not display_gap.empty:
        styled_df = (
            display_gap
            .sort_values(["demand_count", "match_confidence"], ascending=[False, True])
            .reset_index(drop=True)
            .style.apply(highlight_gap, axis=1)
            .format({"match_confidence": "{:.1f}%"})
        )
        st.dataframe(
            styled_df,
            column_config={
                "skill": st.column_config.TextColumn("In-Demand Skill", width="medium"),
                "demand_count": st.column_config.NumberColumn("Demand", format="%d", width="small"),
                "gap_status": st.column_config.TextColumn("Status", width="small"),
                "match_confidence": st.column_config.NumberColumn("Confidence", width="small"),
                "matched_course": st.column_config.TextColumn("Best Matched Course", width="large"),
            },
            use_container_width=True,
            hide_index=True,
            height=520,
        )
    else:
        st.info("No skills match the current filter criteria. Adjust the sidebar filters.")

    # Download button
    gap_csv = display_gap.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥  Download Gap Report CSV",
        data=gap_csv,
        file_name="skill_gap_report_ps26134.csv",
        mime="text/csv",
    )


# ── TAB 2: Course Health Audit ──────────────────────────────────────────────
with tab_courses:
    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-title">Course Health Audit</div>
            <div class="sec-desc">
                Each vocational course is rated by how many of its taught skills
                are still demanded by industry —
                <span class="pill pill-covered">🟢 Aligned</span>
                <span class="pill pill-partial">🟡 Needs Update</span>
                <span class="pill pill-missing">🔴 Obsolete</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Build a set of in-demand skills (lowercase) for matching
    demanded_skills_lower = set(filtered_demand["skill"].str.lower().tolist())

    course_records = []
    for _, c_row in curr_df.iterrows():
        c_id = c_row["course_id"]
        c_name = c_row["course_name"]
        c_sector = str(c_row.get("sector", ""))
        skills_raw = str(c_row.get("skills_taught", ""))
        taught_list = [s.strip() for s in skills_raw.split(",") if s.strip()]
        total_taught = len(taught_list)

        if total_taught == 0:
            course_records.append({
                "course_id": c_id,
                "course_name": c_name,
                "sector": c_sector,
                "skills_taught": skills_raw,
                "total_skills": 0,
                "covered_skills": 0,
                "coverage_pct": 0.0,
                "health": "🔴 Obsolete",
                "covered_list": "",
                "gap_list": skills_raw,
            })
            continue

        covered = [s for s in taught_list if s.strip().lower() in demanded_skills_lower]
        gaps = [s for s in taught_list if s.strip().lower() not in demanded_skills_lower]
        coverage_pct = round(len(covered) / total_taught * 100, 1)

        if coverage_pct >= 70:
            health = "🟢 Aligned"
        elif coverage_pct >= 40:
            health = "🟡 Needs Update"
        else:
            health = "🔴 Obsolete"

        course_records.append({
            "course_id": c_id,
            "course_name": c_name,
            "sector": c_sector,
            "skills_taught": skills_raw,
            "total_skills": total_taught,
            "covered_skills": len(covered),
            "coverage_pct": coverage_pct,
            "health": health,
            "covered_list": ", ".join(covered),
            "gap_list": ", ".join(gaps),
        })

    course_health_df = pd.DataFrame(course_records)

    # Summary metrics
    ch_col1, ch_col2, ch_col3, ch_col4 = st.columns(4)
    aligned_count = len(course_health_df[course_health_df["health"].str.contains("Aligned")])
    needs_count = len(course_health_df[course_health_df["health"].str.contains("Needs Update")])
    obsolete_count = len(course_health_df[course_health_df["health"].str.contains("Obsolete")])
    avg_coverage = round(course_health_df["coverage_pct"].mean(), 1)

    ch_col1.metric("Total Courses", len(course_health_df))
    ch_col2.metric("🟢 Aligned", aligned_count)
    ch_col3.metric("🟡 Needs Update", needs_count)
    ch_col4.metric("🔴 Obsolete", obsolete_count)

    st.markdown("")

    # Course health table
    def highlight_health(row):
        h = row["health"]
        if "Aligned" in h:
            return ["background-color: rgba(16,185,129,0.08); color: #34D399"] * len(row)
        elif "Needs Update" in h:
            return ["background-color: rgba(245,158,11,0.08); color: #FBBF24"] * len(row)
        else:
            return ["background-color: rgba(239,68,68,0.08); color: #F87171"] * len(row)

    display_health = course_health_df[["course_id", "course_name", "sector", "total_skills", "covered_skills", "coverage_pct", "health", "gap_list"]].copy()
    display_health = display_health.rename(columns={
        "course_id": "Course ID",
        "course_name": "Course Name",
        "sector": "Sector",
        "total_skills": "Total Skills",
        "covered_skills": "Demanded Skills",
        "coverage_pct": "Coverage %",
        "health": "Health Rating",
        "gap_list": "Skills Not In Demand",
    })

    styled_health = (
        display_health
        .style
        .apply(lambda row: highlight_health(pd.Series({"health": row["Health Rating"]})), axis=1)
        .format({"Coverage %": "{:.1f}%"})
    )

    st.dataframe(
        styled_health,
        use_container_width=True,
        hide_index=True,
        height=480,
    )

    # Detailed course cards
    st.markdown("#### Detailed Course Breakdown")
    for _, cr in course_health_df.iterrows():
        if "Aligned" in cr["health"]:
            icon = "🟢"
            pill_class = "pill-covered"
        elif "Needs Update" in cr["health"]:
            icon = "🟡"
            pill_class = "pill-partial"
        else:
            icon = "🔴"
            pill_class = "pill-missing"

        gap_text = f'<br/><span style="color:var(--red); font-size:0.78rem;">⚠ Not in demand: {cr["gap_list"]}</span>' if cr["gap_list"] else ""

        st.markdown(
            f"""
            <div class="course-card">
                <div class="badge-icon">{icon}</div>
                <div class="course-info">
                    <div class="course-name">{cr['course_name']}</div>
                    <div class="course-sector">{cr['sector']} · {cr['course_id']}</div>
                    <div class="course-skills">
                        <strong>{cr['covered_skills']}/{cr['total_skills']}</strong> skills aligned with industry demand
                        ({cr['coverage_pct']}%)
                        {gap_text}
                    </div>
                </div>
                <div class="health-badge">
                    <span class="pill {pill_class}">{cr['health']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    course_csv = course_health_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥  Download Course Health Report CSV",
        data=course_csv,
        file_name="course_health_audit_ps26134.csv",
        mime="text/csv",
    )


# ── TAB 3: Trainer Development ──────────────────────────────────────────────
with tab_trainer:
    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-title">Trainer Development & Faculty Upskilling Roadmap</div>
            <div class="sec-desc">
                Actionable intervention plan for ITI/vocational faculty — prioritised
                by market demand and curriculum gap severity.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if filtered_trainer.empty:
        st.success("All tracked skills are adequately covered by current curricula — no trainer interventions required!")
    else:
        col_m1, col_m2, col_m3 = st.columns(3)
        high_priority = filtered_trainer[filtered_trainer["demand_count"] >= 2]
        col_m1.metric("Total Interventions", len(filtered_trainer))
        col_m2.metric("High-Demand Priority", len(high_priority))
        col_m3.metric("Emerging Skills", len(filtered_trainer) - len(high_priority))

        st.markdown("")  # spacer

        for _, row in filtered_trainer.iterrows():
            border_color = "var(--red)" if row["demand_count"] >= 2 else "var(--amber)"
            st.markdown(
                f"""
                <div class="trainer-card" style="border-left-color:{border_color}">
                    <strong>{row['skill']}</strong>
                    &nbsp;<span class="pill {'pill-missing' if row['demand_count'] >= 2 else 'pill-partial'}"
                    >demand: {row['demand_count']}</span>
                    <div class="reason">{row['reason']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        trainer_csv = filtered_trainer.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥  Export Trainer Roadmap CSV",
            data=trainer_csv,
            file_name="trainer_roadmap_ps26134.csv",
            mime="text/csv",
        )


# ── TAB 3: Sector & District ────────────────────────────────────────────────
with tab_explore:
    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-title">Sectoral & Regional Demand Intelligence</div>
            <div class="sec-desc">Hiring patterns across Pune, Nashik, and Nagpur in IT, Automotive, and Textile sectors.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown("#### Jobs by Sector")
        sector_df = jobs_df["sector"].value_counts().reset_index()
        sector_df.columns = ["Sector", "Job Postings"]
        st.bar_chart(sector_df.set_index("Sector"), color="#6366F1", height=300)

    with col_v2:
        st.markdown("#### Jobs by District")
        district_df = jobs_df["district"].value_counts().reset_index()
        district_df.columns = ["District", "Job Postings"]
        st.bar_chart(district_df.set_index("District"), color="#A855F7", height=300)

    st.markdown("#### Top In-Demand Skills (Filtered View)")
    st.dataframe(
        filtered_demand.head(20),
        column_config={
            "skill": st.column_config.TextColumn("Skill"),
            "demand_count": st.column_config.NumberColumn("Demand Count", format="%d"),
            "sectors": st.column_config.ListColumn("Sectors"),
            "districts": st.column_config.ListColumn("Districts"),
        },
        use_container_width=True,
        hide_index=True,
    )


# ── TAB 4: Live AI Playground ───────────────────────────────────────────────
with tab_playground:
    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-title">Real-Time spaCy Skill Extractor & Gap Tester</div>
            <div class="sec-desc">
                Paste any job posting or course description to instantly extract
                skills and benchmark against vocational curricula.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    examples = {
        "(Custom Text)": "",
        "Cloud Architect (IT)": "Senior Cloud Architect proficient in Docker, Kubernetes, Terraform, and AWS Cloud with experience in CI/CD pipelines and microservices architecture.",
        "EV Powertrain Specialist (Auto)": "Electric Vehicle Powertrain Specialist with CAN Bus Diagnostics, MATLAB Simulink, Battery Chemistry, and ADAS Sensor Calibration expertise in Pune.",
        "Master Weaver (Textile)": "Master Weaver with deep knowledge of Digital Textile Printing, Sublimation Printing, Shade Matching, and Airjet Loom Maintenance in Nagpur.",
    }
    preset_choice = st.selectbox("Quick Examples", list(examples.keys()))
    user_text = st.text_area(
        "Enter text to analyze:",
        value=examples[preset_choice],
        height=120,
        placeholder="e.g. Looking for a Data Scientist with Python, PyTorch, LangChain and Vector Databases skills...",
    )

    if st.button("🚀  Analyze & Detect Gaps", type="primary", use_container_width=True):
        if not user_text.strip():
            st.warning("Enter some text before analyzing.")
        else:
            with st.spinner("Running spaCy NLP extraction pipeline…"):
                extracted = extract_skills(user_text)

            if not extracted:
                st.warning("No canonical skills detected. Try pasting a more technical job description.")
            else:
                st.success(f"Extracted **{len(extracted)}** skills from input text.")

                mini_demand = pd.DataFrame(
                    [{"skill": s, "demand_count": 1, "sectors": [], "districts": []} for s in extracted]
                )
                mini_gap = detect_gaps(mini_demand, curr_df)
                mini_trainer = flag_trainer_needs(mini_gap)

                res_col1, res_col2 = st.columns([3, 2])

                with res_col1:
                    st.markdown("##### Gap Analysis")
                    styled = (
                        mini_gap.style
                        .apply(highlight_gap, axis=1)
                        .format({"match_confidence": "{:.1f}%"})
                    )
                    st.dataframe(styled, use_container_width=True, hide_index=True)

                with res_col2:
                    st.markdown("##### Trainer Advisory")
                    if mini_trainer.empty:
                        st.info("All extracted skills are covered by existing curricula.")
                    else:
                        for _, r in mini_trainer.iterrows():
                            border = "var(--red)" if r["demand_count"] >= 2 else "var(--amber)"
                            st.markdown(
                                f"""
                                <div class="trainer-card" style="border-left-color:{border}">
                                    <strong>{r['skill']}</strong>
                                    <div class="reason">{r['reason']}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
