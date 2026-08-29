import json
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.load_data import load_all_data
from src.skill_extractor import extract_skills
from src.demand_scorer import compute_demand
from src.gap_detector import detect_gaps, flag_trainer_needs
from src.live_fetcher import fetch_live_jobs_adzuna, generate_demo_live_jobs

FEEDBACK_FILE = PROJECT_ROOT / "data" / "feedback_log.json"


def log_feedback(skill: str, course: str, gap_status: str, user_response: str):
    """
    Appends {skill, course, gap_status, user_response, timestamp} to data/feedback_log.json.
    Automatically creates the file and parent directory if it does not exist yet.
    """
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    logs = []
    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, list):
                    logs = content
        except Exception:
            logs = []

    entry = {
        "skill": skill,
        "course": course,
        "gap_status": gap_status,
        "user_response": user_response,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    logs.append(entry)

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    return entry

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Skill-Industry Alignment Dashboard — PS 26134",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Glass UI Design System ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --mono: 'JetBrains Mono', monospace;
  --glass: rgba(255,255,255,0.035);
  --glass-hover: rgba(255,255,255,0.06);
  --glass-border: rgba(255,255,255,0.08);
  --glass-border-hover: rgba(255,255,255,0.16);
  --surface: rgba(10,10,20,0.92);
  --text-1: #F0F2F5;
  --text-2: #9CA3AF;
  --text-3: #6B7280;
  --accent: #7C3AED;
  --accent-glow: rgba(124,58,237,0.18);
  --green: #10B981; --green-bg: rgba(16,185,129,0.1); --green-border: rgba(16,185,129,0.25);
  --amber: #F59E0B; --amber-bg: rgba(245,158,11,0.1); --amber-border: rgba(245,158,11,0.25);
  --red: #EF4444;   --red-bg: rgba(239,68,68,0.1);   --red-border: rgba(239,68,68,0.25);
  --spring: all 0.35s cubic-bezier(0.16,1,0.3,1);
  --r: 16px;
}

* { font-family: var(--sans) !important; }
code, pre, .stCode { font-family: var(--mono) !important; }

.block-container { padding-top: 1.2rem !important; padding-bottom: 3rem !important; max-width: 1440px !important; }

/* ── Hero ──────────────────────────────────────────────────────────────────── */
.hero {
  background: var(--surface);
  backdrop-filter: blur(40px) saturate(1.6);
  -webkit-backdrop-filter: blur(40px) saturate(1.6);
  border: 1px solid var(--glass-border);
  border-radius: var(--r);
  padding: 2.2rem 2.6rem 2rem;
  margin-bottom: 1.6rem;
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: "";
  position: absolute;
  top: -100px; right: -60px;
  width: 360px; height: 360px;
  background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
  pointer-events: none;
}
.hero::after {
  content: "";
  position: absolute;
  bottom: -80px; left: 30%;
  width: 280px; height: 200px;
  background: radial-gradient(circle, rgba(16,185,129,0.08) 0%, transparent 70%);
  pointer-events: none;
}
.hero h1 {
  font-size: 2rem; font-weight: 800; letter-spacing: -0.04em;
  color: #FFF; margin: 0; line-height: 1.2;
}
.hero .tag {
  display: inline-flex; align-items: center;
  padding: 0.18rem 0.6rem; border-radius: 99px;
  font-size: 0.65rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  background: var(--accent-glow); color: #C4B5FD; border: 1px solid rgba(124,58,237,0.3);
  margin-left: 0.65rem; vertical-align: middle;
}
.hero p { font-size: 0.92rem; color: var(--text-2); margin: 0.6rem 0 0; max-width: 800px; line-height: 1.7; }

/* ── Glass Cards ───────────────────────────────────────────────────────────── */
.g-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(185px,1fr)); gap: 0.9rem; margin-bottom: 1.5rem; }
.g-card {
  background: var(--glass);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid var(--glass-border);
  border-radius: 14px;
  padding: 1.1rem 1.25rem;
  transition: var(--spring);
}
.g-card:hover { transform: translateY(-2px); border-color: var(--glass-border-hover); box-shadow: 0 12px 28px -8px rgba(0,0,0,0.25); }
.g-card .label { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-3); }
.g-card .val { font-size: 1.75rem; font-weight: 800; letter-spacing: -0.04em; color: var(--text-1); margin-top: 0.15rem; }
.g-card .sub { font-size: 0.7rem; color: var(--text-3); margin-top: 0.15rem; }

/* ── Section Headers ───────────────────────────────────────────────────────── */
.sh { margin: 1.2rem 0 0.7rem; }
.sh-title { font-size: 1.15rem; font-weight: 700; color: var(--text-1); letter-spacing: -0.02em; }
.sh-desc { font-size: 0.82rem; color: var(--text-2); margin-top: 0.1rem; }

/* ── Pills ─────────────────────────────────────────────────────────────────── */
.p { display:inline-flex; align-items:center; padding:0.18rem 0.55rem; border-radius:99px; font-size:0.67rem; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; margin:0 0.15rem; }
.p-g { background:var(--green-bg); color:var(--green); border:1px solid var(--green-border); }
.p-y { background:var(--amber-bg); color:var(--amber); border:1px solid var(--amber-border); }
.p-r { background:var(--red-bg);   color:var(--red);   border:1px solid var(--red-border); }

/* ── Trainer Panel ─────────────────────────────────────────────────────────── */
.tp {
  background: var(--glass);
  backdrop-filter: blur(20px);
  border: 1px solid var(--amber-border);
  border-radius: var(--r);
  padding: 1.3rem 1.5rem;
  margin: 0.8rem 0 1.5rem;
}
.tp-head { display:flex; align-items:center; gap:0.55rem; margin-bottom:0.65rem; }
.tp-title { font-size:1rem; font-weight:700; color:var(--text-1); }
.tp-badge { font-size:0.65rem; font-weight:700; padding:0.12rem 0.5rem; border-radius:99px; background:var(--red-bg); color:var(--red); border:1px solid var(--red-border); }
.chip-grid { display:flex; flex-wrap:wrap; gap:0.4rem; }
.chip {
  display:inline-flex; align-items:center; gap:4px;
  padding:0.25rem 0.65rem; border-radius:99px;
  font-size:0.72rem; font-weight:600; transition:var(--spring); cursor:default;
}
.chip:hover { transform:translateY(-1px); }
.chip-r { background:var(--red-bg); color:var(--red); border:1px solid var(--red-border); }
.chip-y { background:var(--amber-bg); color:var(--amber); border:1px solid var(--amber-border); }

/* ── Course Cards ──────────────────────────────────────────────────────────── */
.cc {
  background: var(--glass);
  backdrop-filter: blur(16px);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  padding: 0.9rem 1.1rem;
  margin-bottom: 0.55rem;
  display: flex; align-items: flex-start; gap: 0.85rem;
  transition: var(--spring);
}
.cc:hover { background:var(--glass-hover); transform:translateY(-1px); }
.cc .icon { font-size:1.4rem; flex-shrink:0; }
.cc .info { flex:1; }
.cc .name { font-size:0.9rem; font-weight:700; color:var(--text-1); }
.cc .meta { font-size:0.7rem; font-weight:600; color:var(--text-3); text-transform:uppercase; letter-spacing:0.05em; margin-top:1px; }
.cc .detail { font-size:0.78rem; color:var(--text-2); margin-top:0.3rem; line-height:1.5; }
.cc .hb { flex-shrink:0; }

/* ── Trainer cards ─────────────────────────────────────────────────────────── */
.tc {
  background: var(--glass);
  border-left: 3px solid var(--amber);
  border-radius: 0 10px 10px 0;
  padding: 0.8rem 1rem;
  margin-bottom: 0.5rem;
  transition: var(--spring);
}
.tc:hover { background:var(--glass-hover); transform:translateX(3px); }
.tc strong { color:var(--text-1); font-size:0.88rem; }
.tc .rsn { color:var(--text-2); font-size:0.78rem; line-height:1.5; margin-top:0.2rem; }

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: rgba(8,8,18,0.97) !important;
  border-right: 1px solid var(--glass-border) !important;
}
section[data-testid="stSidebar"] .stMarkdown h3 {
  font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:var(--text-3); margin-top:0.8rem;
}

/* ── Error ──────────────────────────────────────────────────────────────────── */
.err-box {
  text-align:center; padding:3rem 2rem;
  background:var(--glass); border:1px dashed var(--red-border);
  border-radius:var(--r); margin:3rem auto; max-width:580px;
}
.err-box .ic { font-size:2.8rem; margin-bottom:0.6rem; }
.err-box h2 { color:var(--red); font-size:1.15rem; font-weight:700; margin:0 0 0.4rem; }
.err-box p { color:var(--text-2); font-size:0.88rem; line-height:1.6; }
</style>
""", unsafe_allow_html=True)


# ─── Pipeline ────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def run_pipeline():
    jobs_df, curr_df = load_all_data()
    if jobs_df is None:
        raise FileNotFoundError(
            "Could not load <code>data/jobs_sample.csv</code>. "
            "Ensure it exists with columns: job_id, job_title, sector, district, job_description."
        )
    if curr_df is None:
        raise FileNotFoundError(
            "Could not load <code>data/curriculum_sample.csv</code>. "
            "Ensure it exists with columns: course_id, course_name, sector, skills_taught."
        )
    demand_df = compute_demand(jobs_df)
    gap_df = detect_gaps(demand_df, curr_df)
    trainer_df = flag_trainer_needs(gap_df)
    return {"jobs": jobs_df, "curriculum": curr_df, "demand": demand_df, "gap": gap_df, "trainer": trainer_df}


try:
    data = run_pipeline()
    ok = True
except Exception as e:
    data = None
    ok = False
    err_msg = str(e)


# ─── Hero ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🎯 Skill-Industry Alignment Dashboard<span class="tag">PS 26134</span></h1>
  <p>NLP-powered intelligence matching <strong>industry job demand</strong> against
  <strong>vocational training curricula</strong> across Maharashtra's IT, Automotive &amp;
  Textile sectors — surfacing skill gaps and generating <strong>trainer development roadmaps</strong>.</p>
</div>
""", unsafe_allow_html=True)

if not ok:
    st.markdown(f"""
    <div class="err-box">
      <div class="ic">📂</div>
      <h2>Data Not Available</h2>
      <p>{err_msg}</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── Live Job Session State Management ──────────────────────────────────────
if "live_jobs" not in st.session_state:
    st.session_state["live_jobs"] = pd.DataFrame(columns=["job_id", "job_title", "sector", "district", "job_description"])

baseline_jobs_df = data["jobs"]
curr_df = data["curriculum"]

# Combine baseline jobs with live-ingested jobs
if not st.session_state["live_jobs"].empty:
    jobs_df = pd.concat([baseline_jobs_df, st.session_state["live_jobs"]], ignore_index=True)
else:
    jobs_df = baseline_jobs_df

demand_df = compute_demand(jobs_df)
gap_df = detect_gaps(demand_df, curr_df)
trainer_df = flag_trainer_needs(gap_df)


# ─── Sidebar Filters & Live Ingestion ───────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚡ Live Market Ingestion (Adzuna)")
    live_sec = st.selectbox("Sector for Live Feed", ["IT", "Automotive", "Textile"], index=0, key="live_sec_sel")
    live_dist = st.selectbox("District for Live Feed", ["Pune", "Nashik", "Nagpur"], index=0, key="live_dist_sel")
    live_cnt = st.slider("Number of jobs", min_value=5, max_value=10, value=6, key="live_cnt_sel")

    # Fetch Live Jobs Now Button
    if st.button("🚀 Fetch Live Jobs Now", type="primary", use_container_width=True):
        with st.spinner(f"Calling Adzuna API for {live_sec} jobs in {live_dist}..."):
            new_jobs, err = fetch_live_jobs_adzuna(live_sec, live_dist, live_cnt)

            if err:
                st.warning(f"⚠️ {err}")
                # Provide instant demo fallback option
                st.info("💡 You can click the test button below to simulate live API ingestion with a fresh batch of realistic market jobs.")
            elif new_jobs is not None and not new_jobs.empty:
                st.session_state["live_jobs"] = pd.concat([st.session_state["live_jobs"], new_jobs], ignore_index=True)
                st.success(f"✅ Ingested {len(new_jobs)} live job postings from Adzuna!")
                st.rerun()

    # Instant Demo Simulation Button (when credentials are not yet added to .env)
    if st.button("🧪 Test Ingestion with Demo Live Batch (5 Jobs)", use_container_width=True):
        demo_jobs = generate_demo_live_jobs(live_sec, live_dist, count=5)
        st.session_state["live_jobs"] = pd.concat([st.session_state["live_jobs"], demo_jobs], ignore_index=True)
        st.success(f"✅ Ingested 5 live {live_sec} market postings for {live_dist}!")
        st.rerun()

    if not st.session_state["live_jobs"].empty:
        st.caption(f"Currently tracking **{len(st.session_state['live_jobs'])} live ingested jobs**.")
        if st.button("🔄 Reset to Baseline (20 Jobs)", use_container_width=True):
            st.session_state["live_jobs"] = pd.DataFrame(columns=["job_id", "job_title", "sector", "district", "job_description"])
            st.rerun()

    st.markdown("---")
    st.markdown("### 🏷️ Sector")
    all_sectors = sorted(jobs_df["sector"].dropna().unique().tolist())
    sel_sectors = st.multiselect("Sectors", all_sectors, default=all_sectors, label_visibility="collapsed")

    st.markdown("### 📍 District")
    all_districts = sorted(jobs_df["district"].dropna().unique().tolist())
    sel_districts = st.multiselect("Districts", all_districts, default=all_districts, label_visibility="collapsed")

    st.markdown("### 🚦 Gap Status")
    sel_statuses = st.multiselect("Status", ["covered", "partial", "missing"], default=["covered", "partial", "missing"], label_visibility="collapsed")

    st.markdown("### 🔎 Search")
    q_search = st.text_input("Search", placeholder="Docker, Battery, Weaving…", label_visibility="collapsed")

    st.divider()
    st.caption("SkillTrack AI · PS 26134")
    st.caption("spaCy en_core_web_sm · rapidfuzz ≥ 80")


# ─── Filter Logic ───────────────────────────────────────────────────────────
mask = demand_df.apply(
    lambda r: any(s in sel_sectors for s in r["sectors"]) and any(d in sel_districts for d in r["districts"]),
    axis=1,
)
f_demand = demand_df[mask].copy()
f_gap = detect_gaps(f_demand, curr_df)
f_trainer = flag_trainer_needs(f_gap)

disp_gap = f_gap[f_gap["gap_status"].isin(sel_statuses)].copy() if sel_statuses else f_gap.copy()
if q_search.strip():
    qs = q_search.strip().lower()
    disp_gap = disp_gap[disp_gap["skill"].str.lower().str.contains(qs, na=False) | disp_gap["matched_course"].str.lower().str.contains(qs, na=False)]


# ─── KPI Bar ────────────────────────────────────────────────────────────────
n_skills = len(f_gap)
n_cov = len(f_gap[f_gap["gap_status"] == "covered"])
n_par = len(f_gap[f_gap["gap_status"] == "partial"])
n_mis = len(f_gap[f_gap["gap_status"] == "missing"])
align_pct = round(n_cov / n_skills * 100, 1) if n_skills else 0

live_count_text = f" ({len(st.session_state['live_jobs'])} live)" if not st.session_state["live_jobs"].empty else ""

st.markdown(f"""
<div class="g-row">
  <div class="g-card"><div class="label">Jobs Analyzed</div><div class="val">{len(jobs_df)}<span style='font-size:0.9rem; color:#A855F7;'>{live_count_text}</span></div><div class="sub">{len(sel_sectors)} sectors · {len(sel_districts)} districts</div></div>
  <div class="g-card"><div class="label">Skills Tracked</div><div class="val">{n_skills}</div><div class="sub">spaCy NLP extraction</div></div>
  <div class="g-card"><div class="label" style="color:var(--green)">✓ Covered</div><div class="val" style="color:var(--green)">{n_cov}</div><div class="sub">{align_pct}% alignment</div></div>
  <div class="g-card"><div class="label" style="color:var(--amber)">⚠ Partial</div><div class="val" style="color:var(--amber)">{n_par}</div><div class="sub">50–80% match</div></div>
  <div class="g-card"><div class="label" style="color:var(--red)">✕ Missing</div><div class="val" style="color:var(--red)">{n_mis}</div><div class="sub">&lt;50% match</div></div>
  <div class="g-card" style="border-color:var(--red-border)"><div class="label" style="color:var(--red)">Trainer Priority</div><div class="val" style="color:var(--red)">{len(f_trainer)}</div><div class="sub">Faculty actions needed</div></div>
</div>
""", unsafe_allow_html=True)


# ─── Trainer Upskilling Panel (always visible) ──────────────────────────────
if not f_trainer.empty:
    chips = ""
    for _, r in f_trainer[f_trainer["demand_count"] >= 2].sort_values("demand_count", ascending=False).iterrows():
        chips += f'<span class="chip chip-r">🔴 {r["skill"]} ({r["demand_count"]})</span>'
    for _, r in f_trainer[f_trainer["demand_count"] < 2].sort_values("skill").iterrows():
        chips += f'<span class="chip chip-y">🟡 {r["skill"]}</span>'
    st.markdown(f"""
    <div class="tp">
      <div class="tp-head">
        <span style="font-size:1.2rem">👨‍🏫</span>
        <span class="tp-title">Trainer Upskilling Needed</span>
        <span class="tp-badge">{len(f_trainer)} flagged</span>
      </div>
      <div class="chip-grid">{chips}</div>
    </div>
    """, unsafe_allow_html=True)


# ─── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🔍 Skill Gap Matrix",
    "🏫 Course Health Audit",
    "👨‍🏫 Trainer Planner",
    "📊 Regional View",
    "🧪 AI Playground",
])


# ═══ TAB 1 — Gap Matrix ═════════════════════════════════════════════════════
with tab1:
    st.markdown("""
    <div class="sh"><div class="sh-title">Curriculum Alignment &amp; Gap Matrix</div>
    <div class="sh-desc">Fuzzy matching via rapidfuzz —
      <span class="p p-g">covered &gt;80%</span>
      <span class="p p-y">partial 50–80%</span>
      <span class="p p-r">missing &lt;50%</span></div></div>
    """, unsafe_allow_html=True)

    # Top 10 bar chart
    st.markdown("#### Top 10 In-Demand Skills")
    top10 = f_demand.sort_values("demand_count", ascending=False).head(10).copy()
    if not top10.empty:
        st.bar_chart(top10[["skill", "demand_count"]].set_index("skill"), color="#7C3AED", height=300)

    st.markdown("#### Interactive Skill Gap Matrix & Human-in-the-Loop Feedback")
    st.caption("Review AI-detected curriculum alignments and click **Agree** or **Disagree** to calibrate the engine.")

    if disp_gap.empty:
        st.info("No skills match the selected filter criteria. Adjust the sidebar filters.")
    else:
        # Sort rows by demand descending, then confidence ascending
        sorted_gap = (
            disp_gap.sort_values(["demand_count", "match_confidence"], ascending=[False, True])
            .reset_index(drop=True)
        )

        # Pagination / View controls
        page_col1, page_col2 = st.columns([1, 4])
        with page_col1:
            page_size = st.selectbox("Rows per page", [10, 20, 50, "All"], index=0, key="gap_page_size")
        
        total_rows = len(sorted_gap)
        if page_size == "All":
            num_pages = 1
            current_page = 1
            page_rows = sorted_gap
        else:
            num_pages = max(1, (total_rows + page_size - 1) // page_size)
            with page_col2:
                current_page = st.number_input(f"Page (1 to {num_pages})", min_value=1, max_value=num_pages, value=1, step=1, key="gap_page_num")
            start_idx = (current_page - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            page_rows = sorted_gap.iloc[start_idx:end_idx]

        st.caption(f"Showing rows {start_idx + 1 if page_size != 'All' else 1}–{end_idx if page_size != 'All' else total_rows} of {total_rows} skills.")

        # Interactive Table Header
        h_c1, h_c2, h_c3, h_c4, h_c5, h_c6, h_c7 = st.columns([2.5, 1, 1.2, 1, 3, 1.1, 1.1])
        h_c1.markdown("**In-Demand Skill**")
        h_c2.markdown("**Demand**")
        h_c3.markdown("**Gap Status**")
        h_c4.markdown("**Match %**")
        h_c5.markdown("**Best Matched Course**")
        h_c6.markdown("**Feedback**")
        h_c7.markdown("")

        st.markdown("<hr style='margin:0.2rem 0 0.6rem; border-color:var(--glass-border);'>", unsafe_allow_html=True)

        # Render each row with Agree / Disagree buttons
        for idx, row in page_rows.iterrows():
            skill_name = str(row["skill"])
            demand_num = int(row["demand_count"])
            gap_stat = str(row["gap_status"])
            conf_val = float(row["match_confidence"])
            course_val = str(row["matched_course"])

            # Determine status pill
            if gap_stat == "covered":
                pill_html = '<span class="p p-g">Covered</span>'
            elif gap_stat == "partial":
                pill_html = '<span class="p p-y">Partial</span>'
            else:
                pill_html = '<span class="p p-r">Missing</span>'

            r_c1, r_c2, r_c3, r_c4, r_c5, r_c6, r_c7 = st.columns([2.5, 1, 1.2, 1, 3, 1.1, 1.1])

            r_c1.markdown(f"**{skill_name}**")
            r_c2.markdown(f"<span style='color:var(--text-2); font-weight:600;'>{demand_num}</span>", unsafe_allow_html=True)
            r_c3.markdown(pill_html, unsafe_allow_html=True)
            r_c4.markdown(f"<span style='font-family:var(--mono); color:var(--text-2);'>{conf_val:.1f}%</span>", unsafe_allow_html=True)
            r_c5.markdown(f"<span style='font-size:0.85rem; color:var(--text-1);'>{course_val}</span>", unsafe_allow_html=True)

            if r_c6.button("👍 Agree", key=f"btn_agree_{idx}_{skill_name}", use_container_width=True):
                entry = log_feedback(skill_name, course_val, gap_stat, "Agree")
                st.success(f"Feedback logged: **Agree** on '{skill_name}' (matched with '{course_val}')")
                st.toast(f"✅ Saved Agree for {skill_name}")

            if r_c7.button("👎 Disagree", key=f"btn_disagree_{idx}_{skill_name}", use_container_width=True):
                entry = log_feedback(skill_name, course_val, gap_stat, "Disagree")
                st.warning(f"Feedback logged: **Disagree** on '{skill_name}' (flagged for review)")
                st.toast(f"⚠️ Saved Disagree for {skill_name}")

            st.markdown("<hr style='margin:0.2rem 0; border-color:rgba(255,255,255,0.04);'>", unsafe_allow_html=True)

    st.markdown("")
    dl_col1, dl_col2 = st.columns([2, 2])
    with dl_col1:
        st.download_button("📥 Download Gap Report (CSV)", disp_gap.to_csv(index=False).encode(), "skill_gap_report.csv", "text/csv")

    # Feedback Log Viewer
    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                fb_data = json.load(f)
            if fb_data:
                with st.expander(f"📝 User Feedback Audit Log ({len(fb_data)} entries in data/feedback_log.json)"):
                    fb_df = pd.DataFrame(fb_data)
                    st.dataframe(fb_df, use_container_width=True, hide_index=True)
        except Exception:
            pass

# ═══ TAB 2 — Course Health Audit ════════════════════════════════════════════
with tab2:
    st.markdown("""
    <div class="sh"><div class="sh-title">Course Health Audit</div>
    <div class="sh-desc">Each course rated by industry relevance of its taught skills —
      <span class="p p-g">🟢 Aligned ≥70%</span>
      <span class="p p-y">🟡 Needs Update 40–69%</span>
      <span class="p p-r">🔴 Obsolete &lt;40%</span></div></div>
    """, unsafe_allow_html=True)

    demanded_lower = set(f_demand["skill"].str.lower().tolist())
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

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Courses", len(ch_df))
    c2.metric("🟢 Aligned", len(ch_df[ch_df["Health"].str.contains("Aligned")]))
    c3.metric("🟡 Needs Update", len(ch_df[ch_df["Health"].str.contains("Update")]))
    c4.metric("🔴 Obsolete", len(ch_df[ch_df["Health"].str.contains("Obsolete")]))

    # Color-coded health table (fixed styling — apply returns correct column count)
    def color_health(row):
        h = str(row["Health"])
        if "Aligned" in h:
            return ["background-color:rgba(16,185,129,0.07);color:#34D399"] * len(row)
        elif "Update" in h:
            return ["background-color:rgba(245,158,11,0.07);color:#FBBF24"] * len(row)
        return ["background-color:rgba(239,68,68,0.07);color:#F87171"] * len(row)

    styled_ch = ch_df.style.apply(color_health, axis=1).format({"Coverage %": "{:.1f}%"})
    st.dataframe(styled_ch, use_container_width=True, hide_index=True, height=460)

    # Course detail cards
    st.markdown("#### Detailed Breakdown")
    for _, cr in ch_df.iterrows():
        if "Aligned" in cr["Health"]:
            ic, pc = "🟢", "p-g"
        elif "Update" in cr["Health"]:
            ic, pc = "🟡", "p-y"
        else:
            ic, pc = "🔴", "p-r"
        gap_line = f'<br/><span style="color:var(--red);font-size:0.75rem">⚠ Not in demand: {cr["Gap Skills"]}</span>' if cr["Gap Skills"] else ""
        st.markdown(f"""
        <div class="cc">
          <div class="icon">{ic}</div>
          <div class="info">
            <div class="name">{cr['Course Name']}</div>
            <div class="meta">{cr['Sector']} · {cr['Course ID']}</div>
            <div class="detail"><strong>{cr['Demanded Skills']}/{cr['Total Skills']}</strong> skills aligned ({cr['Coverage %']}%){gap_line}</div>
          </div>
          <div class="hb"><span class="p {pc}">{cr['Health']}</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.download_button("📥 Download Course Health CSV", ch_df.to_csv(index=False).encode(), "course_health_audit.csv", "text/csv")


# ═══ TAB 3 — Trainer Planner ════════════════════════════════════════════════
with tab3:
    st.markdown("""
    <div class="sh"><div class="sh-title">Trainer Development &amp; Faculty Upskilling Roadmap</div>
    <div class="sh-desc">Prioritised intervention plan for ITI/vocational faculty based on market demand &amp; gap severity.</div></div>
    """, unsafe_allow_html=True)

    if f_trainer.empty:
        st.success("All skills covered — no trainer interventions required!")
    else:
        m1, m2, m3 = st.columns(3)
        hp = f_trainer[f_trainer["demand_count"] >= 2]
        m1.metric("Total Interventions", len(f_trainer))
        m2.metric("🔴 High-Demand Priority", len(hp))
        m3.metric("🟡 Emerging Skills", len(f_trainer) - len(hp))

        for _, r in f_trainer.iterrows():
            bc = "var(--red)" if r["demand_count"] >= 2 else "var(--amber)"
            pill = "p-r" if r["demand_count"] >= 2 else "p-y"
            st.markdown(f"""
            <div class="tc" style="border-left-color:{bc}">
              <strong>{r['skill']}</strong> <span class="p {pill}">demand: {r['demand_count']}</span>
              <div class="rsn">{r['reason']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.download_button("📥 Export Trainer Roadmap", f_trainer.to_csv(index=False).encode(), "trainer_roadmap.csv", "text/csv")


# ═══ TAB 4 — Regional View ══════════════════════════════════════════════════
with tab4:
    st.markdown("""
    <div class="sh"><div class="sh-title">Sectoral &amp; Regional Intelligence</div>
    <div class="sh-desc">Hiring demand distribution across Pune, Nashik, Nagpur in IT, Automotive, Textile.</div></div>
    """, unsafe_allow_html=True)

    v1, v2 = st.columns(2)
    with v1:
        st.markdown("#### Jobs by Sector")
        sd = jobs_df["sector"].value_counts().reset_index()
        sd.columns = ["Sector", "Jobs"]
        st.bar_chart(sd.set_index("Sector"), color="#7C3AED", height=280)
    with v2:
        st.markdown("#### Jobs by District")
        dd = jobs_df["district"].value_counts().reset_index()
        dd.columns = ["District", "Jobs"]
        st.bar_chart(dd.set_index("District"), color="#A855F7", height=280)

    st.markdown("#### Top In-Demand Skills")
    st.dataframe(
        f_demand.head(20),
        column_config={
            "skill": st.column_config.TextColumn("Skill"),
            "demand_count": st.column_config.NumberColumn("Demand", format="%d"),
            "sectors": st.column_config.ListColumn("Sectors"),
            "districts": st.column_config.ListColumn("Districts"),
        },
        use_container_width=True, hide_index=True,
    )


# ═══ TAB 5 — AI Playground ══════════════════════════════════════════════════
with tab5:
    st.markdown("""
    <div class="sh"><div class="sh-title">Live spaCy Skill Extractor &amp; Gap Tester</div>
    <div class="sh-desc">Paste any text to test real-time NLP extraction and benchmark against vocational courses.</div></div>
    """, unsafe_allow_html=True)

    examples = {
        "(Custom)": "",
        "Cloud Architect (IT)": "Senior Cloud Architect proficient in Docker, Kubernetes, Terraform, and AWS Cloud with CI/CD pipelines and microservices.",
        "EV Specialist (Auto)": "EV Powertrain Specialist with CAN Bus Diagnostics, MATLAB Simulink, Battery Chemistry, and ADAS Sensor Calibration in Pune.",
        "Master Weaver (Textile)": "Master Weaver with Digital Textile Printing, Sublimation Printing, Shade Matching, and Airjet Loom Maintenance in Nagpur.",
    }
    pick = st.selectbox("Quick Examples", list(examples.keys()))
    txt = st.text_area("Enter text:", value=examples[pick], height=110, placeholder="Paste a job description or course syllabus…")

    if st.button("🚀 Analyze & Detect Gaps", type="primary", use_container_width=True):
        if not txt.strip():
            st.warning("Enter text first.")
        else:
            with st.spinner("Running spaCy NLP…"):
                extr = extract_skills(txt)
            if not extr:
                st.warning("No canonical skills detected. Try a more technical description.")
            else:
                st.success(f"Extracted **{len(extr)}** skills.")
                md = pd.DataFrame([{"skill": s, "demand_count": 1, "sectors": [], "districts": []} for s in extr])
                mg = detect_gaps(md, curr_df)
                mt = flag_trainer_needs(mg)

                rc1, rc2 = st.columns([3, 2])
                with rc1:
                    st.markdown("##### Gap Analysis")
                    st.dataframe(
                        mg.style.apply(color_gap, axis=1).format({"match_confidence": "{:.1f}%"}),
                        use_container_width=True, hide_index=True,
                    )
                with rc2:
                    st.markdown("##### Trainer Advisory")
                    if mt.empty:
                        st.info("All skills covered!")
                    else:
                        for _, r in mt.iterrows():
                            bc = "var(--red)" if r["demand_count"] >= 2 else "var(--amber)"
                            st.markdown(f"""
                            <div class="tc" style="border-left-color:{bc}">
                              <strong>{r['skill']}</strong>
                              <div class="rsn">{r['reason']}</div>
                            </div>
                            """, unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  MODEL FEEDBACK & CONTINUOUS CALIBRATION SECTION                         ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

st.markdown("<hr style='margin: 3rem 0 1.8rem; border-color: var(--glass-border);'>", unsafe_allow_html=True)

# Read feedback_log.json for live validation counter
employer_validations = []
if FEEDBACK_FILE.exists():
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            data_loaded = json.load(f)
            if isinstance(data_loaded, list):
                employer_validations = data_loaded
    except Exception:
        employer_validations = []

total_validated = len(employer_validations)
agreed_count = sum(1 for v in employer_validations if v.get("user_response") == "Agree")
disagreed_count = sum(1 for v in employer_validations if v.get("user_response") == "Disagree")
agreement_pct = round((agreed_count / total_validated * 100), 1) if total_validated > 0 else 0.0

st.markdown(
    f"""
    <div class="tp" style="border-color: rgba(99, 102, 241, 0.35); background: linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(168, 85, 247, 0.05) 100%);">
        <div class="tp-head" style="justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 0.6rem;">
                <span style="font-size: 1.4rem;">🔄</span>
                <span class="tp-title" style="font-size: 1.15rem;">Model Feedback & Continuous Calibration</span>
            </div>
            <span class="tp-badge" style="background: var(--green-bg); color: var(--green); border-color: var(--green-border); font-size: 0.75rem; padding: 0.2rem 0.75rem;">
                Active Evidence-Based Loop
            </span>
        </div>
        <div style="font-size: 1.35rem; font-weight: 800; color: var(--text-1); margin: 0.4rem 0 0.2rem; letter-spacing: -0.02em;">
            ✨ {total_validated} gaps validated by employers so far.
        </div>
        <p style="font-size: 0.85rem; color: var(--text-2); margin: 0 0 1rem; line-height: 1.6;">
            Continuous evidence-based calibration mechanism: employer votes directly tune NLP match confidence thresholds and validate regional curriculum interventions.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

fb_col1, fb_col2, fb_col3 = st.columns(3)
with fb_col1:
    st.metric("Total Validations Recorded", f"{total_validated}", help="Total feedback clicks from industry/employers")
with fb_col2:
    st.metric("Employer Confirmations (Agree)", f"{agreed_count}", delta=f"{agreement_pct}% consensus" if total_validated else None)
with fb_col3:
    st.metric("Flagged for Calibration (Disagree)", f"{disagreed_count}", delta=f"-{disagreed_count}" if disagreed_count else None, delta_color="inverse")

if employer_validations:
    with st.expander("🔍 View All Employer Validation Records", expanded=False):
        fb_display_df = pd.DataFrame(employer_validations)
        st.dataframe(fb_display_df, use_container_width=True, hide_index=True)
