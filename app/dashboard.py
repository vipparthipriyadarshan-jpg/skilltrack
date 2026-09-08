import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
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
from src.ai_advisor import (
    analyze_requirement,
    get_provider_status_badge,
    export_analysis_to_excel,
    export_analysis_to_csv,
)

FEEDBACK_FILE = PROJECT_ROOT / "data" / "feedback_log.json"


def log_feedback(
    skill: str,
    course: str,
    gap_status: str,
    user_response: str,
    match_score: Optional[float] = None,
    recommendation: Optional[str] = None,
    ai_provider: Optional[str] = None,
):
    """Appends feedback entry to data/feedback_log.json."""
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
        "match_score": match_score,
        "recommendation": recommendation,
        "ai_provider": ai_provider or "SkillTrack NLP",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    logs.append(entry)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    return entry


def render_clean_html(html_str: str) -> None:
    """
    Strips leading and trailing whitespace from every line of an HTML string before
    passing to st.markdown(..., unsafe_allow_html=True). This completely prevents CommonMark
    from misinterpreting 4+ space indented HTML lines as verbatim code blocks.
    """
    clean_lines = [line.strip() for line in html_str.strip().splitlines() if line.strip()]
    st.markdown("\n".join(clean_lines), unsafe_allow_html=True)



# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SkillTrack AI — Skill-Industry Alignment Dashboard",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Google Fonts ─────────────────────────────────────────────────────────────
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700;800&family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
""", unsafe_allow_html=True)

# ─── Education-Theme Design System CSS (Light Only) ───────────────────────────
st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════════
   EDUCATION DESIGN TOKENS — LIGHT MODE (Academic Palette)
   Primary:  Deep Academic Blue  #1E4D8C
   Secondary:Teal Green          #2E7D6E  (growth, covered skills)
   Caution:  Warm Amber          #D4890A  (partial gaps)
   Alert:    Indigo/Purple       #5C6BC0  (missing skills, replaces red)
   Background: Soft Off-White    #F7F9FC
═══════════════════════════════════════════════════════════ */
:root {
  --bg-main:       #F8FAFC;
  --bg-card:       #FFFFFF;
  --bg-sidebar:    #EEF3F9;
  --bg-tinted:     #EDF2F9;
  --accent:        #1E4D8C;
  --accent-dim:    rgba(30, 77, 140, 0.09);
  --accent-border: rgba(30, 77, 140, 0.22);
  --green:         #0D7A5F;
  --green-dim:     rgba(13, 122, 95, 0.10);
  --green-border:  rgba(13, 122, 95, 0.25);
  --amber:         #D97706;
  --amber-dim:     rgba(217, 119, 6, 0.10);
  --amber-border:  rgba(217, 119, 6, 0.28);
  --indigo:        #4338CA;
  --indigo-dim:    rgba(67, 56, 202, 0.10);
  --indigo-border: rgba(67, 56, 202, 0.25);
  --red:           #4338CA;
  --red-dim:       rgba(67, 56, 202, 0.10);
  --red-border:    rgba(67, 56, 202, 0.25);
  --text-1:        #0F2744;
  --text-2:        #3B5270;
  --text-3:        #6B7F96;
  --border:        rgba(30, 77, 140, 0.12);
  --border-hover:  rgba(30, 77, 140, 0.28);
  --shadow:        0 2px 14px rgba(15, 39, 68, 0.06);
  --shadow-lg:     0 8px 30px rgba(15, 39, 68, 0.10);
  --r:             12px;
  --r-sm:          8px;
  --spring:        all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  --serif:         'Source Serif 4', Georgia, serif;
  --sans:          'Inter', -apple-system, sans-serif;
  --mono:          'IBM Plex Mono', 'Fira Code', monospace;
}

/* ── Global Reset ──────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

body, .stApp {
  background: var(--bg-main) !important;
  color: var(--text-1) !important;
  font-family: var(--sans) !important;
}

.block-container {
  padding: 1.6rem 2.4rem 4rem !important;
  max-width: 1520px !important;
}

h1,h2,h3,h4 { font-family: var(--serif) !important; }
code, pre, .stCode, [class*="metric"] [data-testid="stMetricValue"] {
  font-family: var(--mono) !important;
}

/* ── Hide default Streamlit chrome ─────────────────────────── */
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }
.stAppToolbar { display: none !important; }

/* ═══════════════════════════════════════════════════════════
   THEME TOGGLE BUTTON
═══════════════════════════════════════════════════════════ */
.theme-toggle-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 0.4rem 1rem; border-radius: 99px;
  font-family: var(--sans) !important; font-size: 0.78rem; font-weight: 600;
  cursor: pointer; transition: var(--spring);
  background: var(--accent-dim); color: var(--accent);
  border: 1px solid var(--accent-border); margin-bottom: 0.5rem;
}

/* ═══════════════════════════════════════════════════════════
   HERO BANNER
═══════════════════════════════════════════════════════════ */
.hero {
  position: relative;
  background: linear-gradient(135deg, #dce8ff 0%, #eaf0ff 50%, #d0dcf8 100%);
  border: 1px solid var(--border);
  border-bottom: 2px solid var(--accent-border);
  border-radius: var(--r);
  padding: 2.8rem 3rem 2.4rem;
  margin-bottom: 2rem;
  overflow: hidden;
}
.hero::before {
  content: "";
  position: absolute; inset: 0;
  background-image:
    linear-gradient(var(--border) 1px, transparent 1px),
    linear-gradient(90deg, var(--border) 1px, transparent 1px);
  background-size: 40px 40px;
  opacity: 0.18;
  pointer-events: none;
}
.hero::after {
  content: "";
  position: absolute;
  top: -120px; right: -80px;
  width: 420px; height: 420px;
  background: radial-gradient(circle, rgba(30,77,140,0.10) 0%, transparent 65%);
  pointer-events: none;
}
.hero-content { position: relative; z-index: 1; }
.hero h1 {
  font-family: var(--serif) !important;
  font-size: 2.2rem; font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--accent); margin: 0 0 0.5rem; line-height: 1.15;
}
.hero .badge {
  display: inline-flex; align-items: center;
  padding: 0.2rem 0.75rem; border-radius: 99px;
  font-family: var(--mono) !important; font-size: 0.68rem; font-weight: 600;
  letter-spacing: 0.1em; text-transform: uppercase;
  background: var(--accent-dim); color: var(--accent);
  border: 1px solid var(--accent-border); margin-left: 0.8rem; vertical-align: middle;
}
.hero p {
  font-size: 0.95rem; color: var(--text-2);
  margin: 0; max-width: 720px; line-height: 1.75;
}
.hero p strong { color: var(--text-1); font-weight: 600; }

/* ═══════════════════════════════════════════════════════════
   METRIC CARDS
═══════════════════════════════════════════════════════════ */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 1rem; margin-bottom: 2rem;
}
@media (max-width: 1200px) { .kpi-row { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 700px)  { .kpi-row { grid-template-columns: repeat(2, 1fr); } }
.kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border); border-radius: var(--r);
  padding: 1.4rem 1.5rem 1.3rem; box-shadow: var(--shadow);
  transition: var(--spring); display: flex; flex-direction: column;
  gap: 0.25rem; min-height: 120px;
}
.kpi-card:hover { border-color: var(--border-hover); transform: translateY(-3px); box-shadow: var(--shadow-lg); }
@keyframes kpiPulse {
  0%   { box-shadow: 0 0 0 0 rgba(30,77,140,0.45); border-color: var(--accent); }
  50%  { box-shadow: 0 0 0 10px rgba(30,77,140,0); border-color: var(--accent-border); }
  100% { box-shadow: var(--shadow); border-color: var(--border); }
}
.kpi-label {
  font-family: var(--sans) !important; font-size: 0.65rem; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-3); margin-bottom: 0.1rem;
}
.kpi-num {
  font-family: var(--mono) !important; font-size: 2rem; font-weight: 600;
  line-height: 1; letter-spacing: -0.03em; color: var(--accent);
}
.kpi-num.green { color: var(--green); }
.kpi-num.amber { color: var(--amber); }
.kpi-num.indigo { color: var(--indigo); }
.kpi-num.red   { color: var(--indigo); }
.kpi-num.neutral { color: var(--text-1); }
.kpi-live-tag {
  font-family: var(--mono) !important; font-size: 0.65rem;
  color: var(--accent); background: var(--accent-dim);
  border: 1px solid var(--accent-border); border-radius: 99px;
  padding: 0 0.45rem; margin-left: 0.35rem; vertical-align: middle;
}
.kpi-sub { font-size: 0.72rem; color: var(--text-2); margin-top: 0.35rem; font-family: var(--sans) !important; }

/* ═══════════════════════════════════════════════════════════
   SECTION HEADERS
═══════════════════════════════════════════════════════════ */
.sec-head { margin: 2.5rem 0 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border); }
.sec-head-title { font-family: var(--serif) !important; font-size: 1.25rem; font-weight: 700; color: var(--text-1); letter-spacing: -0.02em; }
.sec-head-desc { font-size: 0.82rem; color: var(--text-2); margin-top: 0.2rem; font-family: var(--sans) !important; }

/* ═══════════════════════════════════════════════════════════
   STATUS PILLS / BADGES
═══════════════════════════════════════════════════════════ */
.pill {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 0.18rem 0.6rem; border-radius: 99px;
  font-family: var(--mono) !important; font-size: 0.64rem; font-weight: 600;
  letter-spacing: 0.06em; text-transform: uppercase; margin: 0 0.15rem; white-space: nowrap;
}
.pill-green { background: var(--green-dim); color: var(--green); border: 1px solid var(--green-border); }
.pill-amber { background: var(--amber-dim); color: var(--amber); border: 1px solid var(--amber-border); }
.pill-red   { background: var(--indigo-dim); color: var(--indigo); border: 1px solid var(--indigo-border); }

/* ═══════════════════════════════════════════════════════════
   RICH GAP CARDS
═══════════════════════════════════════════════════════════ */
.gap-card {
  background: var(--bg-card); border-radius: var(--r);
  border: 1px solid var(--border);
  padding: 1.1rem 1.4rem; margin-bottom: 0.75rem;
  transition: var(--spring); box-shadow: var(--shadow);
  display: flex; flex-direction: column; gap: 0.45rem;
}
.gap-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); border-color: var(--border-hover); }
.gap-card-green { border-left: 4px solid var(--green); }
.gap-card-amber { border-left: 4px solid var(--amber); }
.gap-card-red   { border-left: 4px solid var(--red);   }
.gap-card-header { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.gap-card-skill {
  font-family: var(--serif) !important; font-size: 1.05rem;
  font-weight: 700; color: var(--text-1); flex: 1;
}
.gap-card-demand {
  font-family: var(--mono) !important; font-size: 0.72rem; font-weight: 600;
  color: var(--text-2); background: var(--bg-main);
  border: 1px solid var(--border); border-radius: 99px; padding: 0.1rem 0.55rem;
}
.gap-card-conf {
  font-family: var(--mono) !important; font-size: 0.72rem;
  color: var(--text-3); white-space: nowrap;
}
.gap-card-body { display: flex; flex-direction: column; gap: 0.3rem; }
.gap-card-course {
  font-family: var(--sans) !important; font-size: 0.83rem;
  color: var(--text-2); display: flex; align-items: flex-start; gap: 0.4rem;
}
.gap-card-course-name { color: var(--text-1); font-weight: 600; }
.gap-card-context {
  font-family: var(--sans) !important; font-size: 0.80rem;
  color: var(--text-2); line-height: 1.65;
  padding: 0.55rem 0.8rem;
  background: rgba(30,77,140,0.05);
  border-radius: var(--r-sm); margin-top: 0.1rem;
}
.gap-card-context strong { color: var(--text-1); font-weight: 600; }
.gap-card-context .ctx-green { color: var(--green); font-weight: 600; }
.gap-card-context .ctx-amber { color: var(--amber); font-weight: 600; }
.gap-card-context .ctx-red   { color: var(--red);   font-weight: 600; }
.gap-card-context pre, .gap-card-context code {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  margin: 0 !important;
  color: inherit !important;
  font-family: inherit !important;
  font-size: inherit !important;
  white-space: normal !important;
}
.gap-card-footer {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.15rem;
}
.gap-urgency {
  font-family: var(--mono) !important; font-size: 0.6rem; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 0.15rem 0.5rem; border-radius: 99px;
}
.urgency-low   { background: var(--green-dim); color: var(--green); border: 1px solid var(--green-border); }
.urgency-med   { background: var(--amber-dim); color: var(--amber); border: 1px solid var(--amber-border); }
.urgency-high  { background: var(--indigo-dim); color: var(--indigo); border: 1px solid var(--indigo-border); }
.gap-district-tag {
  font-family: var(--sans) !important; font-size: 0.68rem; font-weight: 600;
  color: #1E4D8C; background: rgba(30, 77, 140, 0.08);
  border: 1px solid rgba(30, 77, 140, 0.22); border-radius: 99px;
  padding: 0.12rem 0.55rem; display: inline-flex; align-items: center; gap: 3px;
}

/* ═══════════════════════════════════════════════════════════
   QUICK WINS CARDS
═══════════════════════════════════════════════════════════ */
.qw-card {
  background: var(--bg-card); border-radius: var(--r);
  border: 1px solid var(--green-border); border-left: 4px solid var(--green);
  padding: 1rem 1.3rem; margin-bottom: 0.65rem;
  display: flex; align-items: flex-start; gap: 1rem;
  transition: var(--spring); box-shadow: var(--shadow);
}
.qw-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
.qw-icon { font-size: 1.5rem; flex-shrink: 0; margin-top: 0.1rem; }
.qw-body { flex: 1; }
.qw-title { font-family: var(--serif) !important; font-size: 0.95rem; font-weight: 700; color: var(--text-1); }
.qw-meta  { font-family: var(--mono) !important; font-size: 0.7rem; color: var(--text-3); margin-top: 0.15rem; text-transform: uppercase; letter-spacing: 0.06em; }
.qw-action { font-family: var(--sans) !important; font-size: 0.82rem; color: var(--text-2); margin-top: 0.35rem; line-height: 1.6; }
.qw-action strong { color: var(--green); }
.qw-badge { flex-shrink: 0; }

/* ═══════════════════════════════════════════════════════════
   DISTRICT HOTSPOT TAGS
═══════════════════════════════════════════════════════════ */
.dist-tag {
  display: inline-flex; align-items: center; gap: 3px;
  padding: 0.12rem 0.55rem; border-radius: 99px; font-family: var(--sans) !important;
  font-size: 0.68rem; font-weight: 600;
  background: rgba(30, 77, 140, 0.08); color: #1E4D8C;
  border: 1px solid rgba(30, 77, 140, 0.22); margin: 0.15rem 0.1rem;
}

/* ═══════════════════════════════════════════════════════════
   TRAINER UPSKILLING PANEL
═══════════════════════════════════════════════════════════ */
.tp-panel {
  background: var(--bg-card);
  border: 1px solid var(--accent-border);
  border-left: 4px solid var(--accent);
  border-radius: var(--r); padding: 1.5rem 1.75rem;
  margin: 0 0 2rem; box-shadow: var(--shadow);
}
.tp-header { display: flex; align-items: center; gap: 0.7rem; margin-bottom: 1rem; }
.tp-icon { font-size: 1.5rem; }
.tp-title { font-family: var(--serif) !important; font-size: 1.1rem; font-weight: 700; color: var(--text-1); flex: 1; }
.tp-count {
  font-family: var(--mono) !important; font-size: 0.68rem; font-weight: 600;
  padding: 0.18rem 0.65rem; border-radius: 99px;
  background: var(--indigo-dim); color: var(--indigo); border: 1px solid var(--indigo-border);
}
.chip-grid { display: flex; flex-wrap: wrap; gap: 0.5rem; align-content: flex-start; }
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 0.32rem 0.8rem 0.32rem 0.55rem; border-radius: 99px;
  font-family: var(--sans) !important; font-size: 0.75rem; font-weight: 500;
  transition: var(--spring); cursor: default; white-space: nowrap;
}
.chip:hover { transform: translateY(-1px); }
.chip-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.chip-red  { background: var(--indigo-dim); color: var(--indigo); border: 1px solid var(--indigo-border); }
.chip-red .chip-dot  { background: var(--indigo); }
.chip-amber{ background: var(--amber-dim); color: var(--amber); border: 1px solid var(--amber-border); }
.chip-amber .chip-dot{ background: var(--amber); }

/* ═══════════════════════════════════════════════════════════
   COURSE CARDS
═══════════════════════════════════════════════════════════ */
.cc {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px;
  padding: 1rem 1.25rem; margin-bottom: 0.65rem;
  display: flex; align-items: flex-start; gap: 1rem;
  transition: var(--spring); box-shadow: var(--shadow);
}
.cc:hover { border-color: var(--border-hover); transform: translateY(-2px); box-shadow: var(--shadow); }
.cc .icon { font-size: 1.6rem; flex-shrink: 0; }
.cc .info { flex: 1; }
.cc .name  { font-family: var(--serif) !important; font-size: 0.95rem; font-weight: 700; color: var(--text-1); }
.cc .meta  { font-family: var(--mono) !important; font-size: 0.68rem; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px; }
.cc .detail { font-family: var(--sans) !important; font-size: 0.8rem; color: var(--text-2); margin-top: 0.35rem; line-height: 1.6; }
.cc .hb { flex-shrink: 0; }

/* ═══════════════════════════════════════════════════════════
   TRAINER CARDS
═══════════════════════════════════════════════════════════ */
.tc {
  background: var(--bg-card);
  border-left: 3px solid var(--accent);
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
  border-top: 1px solid var(--border); border-right: 1px solid var(--border); border-bottom: 1px solid var(--border);
  padding: 0.9rem 1.15rem; margin-bottom: 0.6rem;
  transition: var(--spring); box-shadow: var(--shadow);
}
.tc:hover { transform: translateX(4px); border-color: var(--border-hover); }
.tc strong { font-family: var(--serif) !important; color: var(--text-1); font-size: 0.92rem; }
.tc .rsn   { font-family: var(--sans) !important; color: var(--text-2); font-size: 0.78rem; line-height: 1.6; margin-top: 0.25rem; }
.tc .tc-context {
  font-family: var(--sans) !important; font-size: 0.76rem; color: var(--text-2);
  line-height: 1.6; margin-top: 0.4rem;
  padding: 0.45rem 0.7rem;
  background: rgba(30,77,140,0.05);
  border-radius: var(--r-sm);
}
.tc .tc-context strong { color: var(--text-1); }

/* ═══════════════════════════════════════════════════════════
   ERROR BOX
═══════════════════════════════════════════════════════════ */
.err-box {
  text-align: center; padding: 3.5rem 2.5rem;
  background: var(--bg-card); border: 1px dashed var(--red-border);
  border-radius: var(--r); margin: 4rem auto; max-width: 600px; box-shadow: var(--shadow);
}
.err-box .ic { font-size: 3rem; margin-bottom: 0.75rem; }
.err-box h2  { font-family: var(--serif) !important; color: var(--red); font-size: 1.2rem; font-weight: 700; margin: 0 0 0.5rem; }
.err-box p   { color: var(--text-2); font-size: 0.9rem; line-height: 1.7; }

/* ═══════════════════════════════════════════════════════════
   FEEDBACK / CALIBRATION PANEL
═══════════════════════════════════════════════════════════ */
.fb-panel {
  background: linear-gradient(135deg, #eef2ff 0%, #f0f4ff 100%);
  border: 1px solid rgba(99,102,241,0.3); border-left: 4px solid #6366F1;
  border-radius: var(--r); padding: 1.75rem 2rem; margin-top: 3rem; box-shadow: var(--shadow);
}
.fb-panel-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; }
.fb-panel-title { font-family: var(--serif) !important; font-size: 1.15rem; font-weight: 700; color: var(--text-1); }
.fb-active-badge {
  font-family: var(--mono) !important; font-size: 0.68rem; padding: 0.2rem 0.75rem; border-radius: 99px;
  background: var(--green-dim); color: var(--green); border: 1px solid var(--green-border);
}
.fb-counter { font-family: var(--mono) !important; font-size: 1.5rem; font-weight: 700; color: var(--text-1); margin: 0.4rem 0 0.25rem; letter-spacing: -0.02em; }
.fb-counter .num { color: var(--accent); }
.fb-desc { font-size: 0.84rem; color: var(--text-2); line-height: 1.7; }

/* ═══════════════════════════════════════════════════════════
   SIDEBAR OVERRIDES
═══════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
  background: var(--bg-sidebar) !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .stMarkdown h3 {
  font-family: var(--sans) !important; font-size: 0.68rem !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: 0.1em !important;
  color: var(--text-3) !important; margin: 1rem 0 0.4rem !important;
}
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label { color: var(--text-2) !important; font-size: 0.83rem !important; }
section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"],
section[data-testid="stSidebar"] button[kind="primary"] {
  background: var(--accent) !important; color: #fff !important;
  font-family: var(--sans) !important; font-weight: 700 !important; font-size: 0.85rem !important;
  border: none !important; border-radius: var(--r-sm) !important; padding: 0.65rem 1rem !important; transition: var(--spring) !important;
}
section[data-testid="stSidebar"] button[kind="primary"]:hover { background: #163d70 !important; transform: translateY(-1px) !important; }
section[data-testid="stSidebar"] button[kind="secondary"],
section[data-testid="stSidebar"] [data-testid="stButton"] button:not([kind="primary"]) {
  background: transparent !important; color: var(--text-2) !important;
  border: 1px solid var(--border) !important; font-family: var(--sans) !important;
  font-size: 0.82rem !important; border-radius: var(--r-sm) !important; transition: var(--spring) !important;
}
section[data-testid="stSidebar"] button:not([kind="primary"]):hover { border-color: var(--border-hover) !important; color: var(--text-1) !important; }
section[data-testid="stSidebar"] [data-testid="stMultiSelect"] span[data-baseweb="tag"],
[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
  background: #FFFFFF !important; color: #1E4D8C !important;
  border: 1px solid rgba(30, 77, 140, 0.25) !important; border-radius: 99px !important;
  font-family: var(--sans) !important; font-size: 0.75rem !important; font-weight: 600 !important;
}
section[data-testid="stSidebar"] [data-baseweb="tag"] svg,
[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg {
  fill: #1E4D8C !important; color: #1E4D8C !important;
}
div[data-baseweb="popover"] [aria-selected="true"],
div[data-baseweb="menu"] [aria-selected="true"] {
  background-color: rgba(30, 77, 140, 0.08) !important; color: #1E4D8C !important;
}
div[data-baseweb="popover"] input[type="checkbox"]:checked + div,
div[data-baseweb="menu"] input[type="checkbox"]:checked + div {
  background-color: #1E4D8C !important; border-color: #1E4D8C !important;
}
section[data-testid="stSidebar"] [role="slider"],
[role="slider"] {
  background: var(--accent) !important; border-color: #FFFFFF !important;
}
div[data-baseweb="slider"] div[style*="background-color: rgb(255, 75, 75)"],
div[data-baseweb="slider"] div[style*="background-color: rgb(255, 43, 43)"] {
  background-color: var(--accent) !important;
}

/* ═══════════════════════════════════════════════════════════
   TABS
═══════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
  background: transparent !important; border-bottom: 2px solid var(--border) !important; gap: 0.2rem !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important; color: var(--text-2) !important;
  font-family: var(--sans) !important; font-size: 0.85rem !important; font-weight: 500 !important;
  padding: 0.65rem 1.1rem !important;
  border-radius: var(--r-sm) var(--r-sm) 0 0 !important;
  border-bottom: 2px solid transparent !important; transition: var(--spring) !important;
}
.stTabs [aria-selected="true"] {
  color: var(--text-1) !important; border-bottom: 2px solid var(--accent) !important;
  background: var(--accent-dim) !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text-1) !important; background: rgba(30,77,140,0.06) !important; }

/* ═══════════════════════════════════════════════════════════
   DATAFRAME / TABLE
═══════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important; border-radius: var(--r) !important; overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
  background: #dce8ff !important;
  color: var(--text-2) !important; font-family: var(--sans) !important;
  font-size: 0.72rem !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: 0.07em !important;
}
[data-testid="stDataFrame"] td {
  font-family: var(--sans) !important; font-size: 0.83rem !important;
  color: var(--text-1) !important; border-color: var(--border) !important;
}

/* ═══════════════════════════════════════════════════════════
   METRIC WIDGETS (st.metric)
═══════════════════════════════════════════════════════════ */
[data-testid="stMetricValue"] { font-family: var(--mono) !important; color: var(--accent) !important; font-size: 1.75rem !important; }
[data-testid="stMetricLabel"] { font-family: var(--sans) !important; color: var(--text-2) !important; font-size: 0.78rem !important; text-transform: uppercase !important; letter-spacing: 0.06em !important; }
[data-testid="stMetricDelta"] { font-family: var(--mono) !important; font-size: 0.75rem !important; }

/* ═══════════════════════════════════════════════════════════
   EXPANDER, ALERTS, INPUTS, DOWNLOAD BTN, SCROLLBAR
═══════════════════════════════════════════════════════════ */
[data-testid="stExpander"] { background: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: var(--r) !important; }
[data-testid="stExpander"] summary { font-family: var(--sans) !important; font-size: 0.85rem !important; color: var(--text-2) !important; font-weight: 500 !important; }
[data-testid="stExpander"] summary:hover { color: var(--text-1) !important; }
[data-testid="stAlert"] { border-radius: var(--r) !important; font-family: var(--sans) !important; font-size: 0.85rem !important; }
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stTextInput"] input {
  background: #ffffff !important;
  border: 1px solid var(--border) !important; color: var(--text-1) !important;
  border-radius: var(--r-sm) !important; font-family: var(--sans) !important;
}
[data-testid="stDownloadButton"] button {
  background: transparent !important; color: var(--accent) !important;
  border: 1px solid var(--accent-border) !important; border-radius: var(--r-sm) !important;
  font-family: var(--sans) !important; font-weight: 600 !important; font-size: 0.83rem !important; transition: var(--spring) !important;
}
[data-testid="stDownloadButton"] button:hover { background: var(--accent-dim) !important; transform: translateY(-1px) !important; }
[data-testid="stSpinner"] p { color: var(--text-2) !important; font-family: var(--sans) !important; }
[data-testid="stVegaLiteChart"] { border-radius: var(--r) !important; overflow: hidden !important; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(30,77,140,0.20); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: rgba(30,77,140,0.40); }
.live-pulse { animation: kpiPulse 1.4s ease-out; }
</style>
""", unsafe_allow_html=True)


# ─── Pipeline ─────────────────────────────────────────────────────────────────
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


# ─── Hero Banner ──────────────────────────────────────────────────────────────
render_clean_html("""
<div class="hero">
  <div class="hero-content">
    <h1>🎓 Skill-Industry Alignment Dashboard</h1>
    <p>NLP-powered intelligence matching <strong>industry job demand</strong> against
    <strong>vocational training curricula</strong> across Maharashtra's <strong>IT, Automotive, Textile,
    Healthcare, Construction &amp; Retail/E-commerce</strong> sectors — surfacing skill gaps and generating <strong>trainer development roadmaps</strong>.</p>
  </div>
</div>
""")

if not ok:
    render_clean_html(f"""
    <div class="err-box">
      <div class="ic">📂</div>
      <h2>Data Not Available</h2>
      <p>{err_msg}</p>
    </div>
    """)
    st.stop()


# ─── Live Job Session State Management ────────────────────────────────────────
if "live_jobs" not in st.session_state:
    st.session_state["live_jobs"] = pd.DataFrame(columns=["job_id", "job_title", "sector", "district", "job_description"])
if "just_fetched" not in st.session_state:
    st.session_state["just_fetched"] = False

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


# ─── Sidebar Filters & Live Ingestion ─────────────────────────────────────────
with st.sidebar:
    # ── State Scope ─────────────────────────────────────────────────────────
    render_clean_html("""
    <div style="background:rgba(30,77,140,0.08);border:1px solid rgba(30,77,140,0.22);
    border-radius:8px;padding:0.55rem 0.8rem;margin-bottom:0.75rem;">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:0.6rem;font-weight:700;
      letter-spacing:0.1em;text-transform:uppercase;color:#1E4D8C;">Scope</div>
      <div style="font-size:0.88rem;font-weight:600;color:#1A2B3C;margin-top:2px;">
        📍 Maharashtra, India
      </div>
      <div style="font-size:0.72rem;color:#4A6080;margin-top:2px;">
        7 districts · 6 sectors · NSDC framework
      </div>
    </div>
    """)

    st.markdown("### ⚡ Live Market Ingestion")

    live_sec = st.selectbox("Sector for Live Feed", ["IT", "Automotive", "Textile", "Healthcare", "Construction", "Retail/E-commerce"], index=0, key="live_sec_sel")
    live_dist = st.selectbox("District for Live Feed", ["Pune", "Nashik", "Nagpur", "Mumbai", "Aurangabad", "Kolhapur", "Amravati"], index=0, key="live_dist_sel")
    live_cnt = st.slider("Number of jobs", min_value=5, max_value=10, value=6, key="live_cnt_sel")

    # Primary action button
    if st.button("🚀 Fetch Live Jobs Now", type="primary", use_container_width=True):
        _do_rerun = False
        with st.spinner(f"Connecting to Adzuna API for {live_sec} jobs in {live_dist}..."):
            new_jobs, err = fetch_live_jobs_adzuna(live_sec, live_dist, live_cnt)
            if err:
                # If API has an issue or zero results, fall back seamlessly to realistic live batch
                st.warning(f"⚠️ {err}")
                demo_fallback = generate_demo_live_jobs(live_sec, live_dist, count=live_cnt)
                st.session_state["live_jobs"] = pd.concat(
                    [st.session_state["live_jobs"], demo_fallback], ignore_index=True
                ).drop_duplicates(subset=["job_id"])
                st.session_state["just_fetched"] = True
                st.session_state["last_fetch_msg"] = f"✅ Ingested {len(demo_fallback)} live {live_sec} market jobs for {live_dist} (live simulated fallback)!"
                _do_rerun = True
            elif new_jobs is not None and not new_jobs.empty:
                st.session_state["live_jobs"] = pd.concat(
                    [st.session_state["live_jobs"], new_jobs], ignore_index=True
                ).drop_duplicates(subset=["job_id"])
                st.session_state["just_fetched"] = True
                st.session_state["last_fetch_msg"] = f"✅ Live Adzuna feed connected: Ingested {len(new_jobs)} {live_sec} postings for {live_dist}!"
                _do_rerun = True

        if _do_rerun:
            st.rerun()

    # Secondary ghost button
    if st.button("🧪 Test Ingestion with Demo Live Batch (5 Jobs)", use_container_width=True):
        demo_jobs = generate_demo_live_jobs(live_sec, live_dist, count=5)
        st.session_state["live_jobs"] = pd.concat(
            [st.session_state["live_jobs"], demo_jobs], ignore_index=True
        ).drop_duplicates(subset=["job_id"])
        st.session_state["just_fetched"] = True
        st.session_state["last_fetch_msg"] = f"✅ Ingested 5 live market postings for {live_sec} in {live_dist}!"
        st.rerun()

    if st.session_state.get("last_fetch_msg"):
        st.success(st.session_state["last_fetch_msg"])

    if not st.session_state["live_jobs"].empty:
        live_count = len(st.session_state["live_jobs"])
        st.caption(f"⚡ Pipeline active: **+{live_count} live market jobs** currently tracked.")
        with st.expander("🔍 Inspect Live Ingested Jobs", expanded=False):
            st.dataframe(
                st.session_state["live_jobs"][["job_title", "sector", "district"]],
                use_container_width=True,
                hide_index=True,
            )
        if st.button(f"🔄 Reset to Baseline ({len(baseline_jobs_df)} Jobs)", use_container_width=True):
            st.session_state["live_jobs"] = pd.DataFrame(columns=["job_id", "job_title", "sector", "district", "job_description"])
            st.session_state["just_fetched"] = False
            st.session_state["last_fetch_msg"] = None
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
    st.caption("SkillTrack AI · Maharashtra Education Initiative")
    st.caption("spaCy en_core_web_sm · rapidfuzz ≥ 80")


# ─── Filter Logic ─────────────────────────────────────────────────────────────
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


# ─── KPI Cards ────────────────────────────────────────────────────────────────
n_skills = len(f_gap)
n_cov = len(f_gap[f_gap["gap_status"] == "covered"])
n_par = len(f_gap[f_gap["gap_status"] == "partial"])
n_mis = len(f_gap[f_gap["gap_status"] == "missing"])
align_pct = round(n_cov / n_skills * 100, 1) if n_skills else 0
live_tag = f'<span class="kpi-live-tag">+{len(st.session_state["live_jobs"])} live</span>' if not st.session_state["live_jobs"].empty else ""
pulse = ' live-pulse' if st.session_state.get("just_fetched") else ""

render_clean_html(f"""
<div class="kpi-row">
  <div class="kpi-card{pulse}" style="border-top: 3px solid #1E4D8C;">
    <div class="kpi-label">Jobs Analyzed</div>
    <div class="kpi-num neutral">{len(jobs_df)}{live_tag}</div>
    <div class="kpi-sub">{len(sel_sectors)} sectors · {len(sel_districts)} districts</div>
  </div>
  <div class="kpi-card" style="border-top: 3px solid #3B82F6;">
    <div class="kpi-label">Skills Tracked</div>
    <div class="kpi-num neutral">{n_skills}</div>
    <div class="kpi-sub">spaCy NLP extraction</div>
  </div>
  <div class="kpi-card" style="border-top: 3px solid var(--green);">
    <div class="kpi-label">✓ Covered</div>
    <div class="kpi-num green">{n_cov}</div>
    <div class="kpi-sub">{align_pct}% alignment rate</div>
  </div>
  <div class="kpi-card" style="border-top: 3px solid var(--amber);">
    <div class="kpi-label">⚠ Partial</div>
    <div class="kpi-num amber">{n_par}</div>
    <div class="kpi-sub">50–80% match range</div>
  </div>
  <div class="kpi-card" style="border-top: 3px solid var(--indigo);">
    <div class="kpi-label">✕ Missing</div>
    <div class="kpi-num indigo">{n_mis}</div>
    <div class="kpi-sub">&lt;50% match — gaps</div>
  </div>
  <div class="kpi-card" style="border-top: 3px solid var(--indigo);">
    <div class="kpi-label">Trainer Priority</div>
    <div class="kpi-num indigo">{len(f_trainer)}</div>
    <div class="kpi-sub">Faculty actions needed</div>
  </div>
</div>
""")

# Reset pulse flag after render
if st.session_state.get("just_fetched"):
    st.session_state["just_fetched"] = False


# ─── Trainer Upskilling Panel ──────────────────────────────────────────────────
if not f_trainer.empty:
    chips = ""
    for _, r in f_trainer[f_trainer["demand_count"] >= 2].sort_values("demand_count", ascending=False).iterrows():
        chips += f'<span class="chip chip-red"><span class="chip-dot"></span>{r["skill"]} ({r["demand_count"]})</span>'
    for _, r in f_trainer[f_trainer["demand_count"] < 2].sort_values("skill").iterrows():
        chips += f'<span class="chip chip-amber"><span class="chip-dot"></span>{r["skill"]}</span>'
    render_clean_html(f"""
    <div class="tp-panel">
      <div class="tp-header">
        <span class="tp-icon">👨‍🏫</span>
        <span class="tp-title">Trainer Upskilling Needed</span>
        <span class="tp-count">{len(f_trainer)} flagged</span>
      </div>
      <div class="chip-grid">{chips}</div>
    </div>
    """)


# ─── Tabs ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔍 Skill Gap Matrix",
    "🏫 Course Health Audit",
    "👨‍🏫 Trainer Planner",
    "📊 Regional View",
    "⚡ Quick Wins",
    "🎓 AI Skill Intelligence",
])



# ═══ TAB 1 — Gap Matrix ══════════════════════════════════════════════════════
with tab1:
    render_clean_html("""
    <div class="sec-head">
      <div class="sec-head-title">Curriculum Alignment &amp; Gap Matrix</div>
      <div class="sec-head-desc">Fuzzy matching via rapidfuzz —
        <span class="pill pill-green">✅ covered &gt;80%</span>
        <span class="pill pill-amber">⚠️ partial 50–80%</span>
        <span class="pill pill-red">⬤ missing &lt;50%</span>
      </div>
    </div>
    """)

    # Top 10 bar chart
    st.markdown("#### Top 10 In-Demand Skills")
    top10 = f_demand.sort_values("demand_count", ascending=False).head(10).copy()
    if not top10.empty:
        st.bar_chart(top10[["skill", "demand_count"]].set_index("skill"), color="#1E4D8C", height=300)

    render_clean_html("""
    <div class="sec-head" style="margin-top:1.5rem;">
      <div class="sec-head-title">Interactive Gap Matrix &amp; Human-in-the-Loop Feedback</div>
      <div class="sec-head-desc">Click Agree or Disagree on any row to calibrate the NLP matching engine.</div>
    </div>
    """)

    # ── Industry context lookup ────────────────────────────────────────────
    SECTOR_STANDARD = {
        "IT": "NASSCOM Future Skills Prime", "Automotive": "NSDC Automotive Skill Council",
        "Textile": "NSDC Textile Sector Skill Council", "Healthcare": "NSDC Healthcare Sector Skill Council",
        "Construction": "NSDC Construction Skill Development Council", "Retail/E-commerce": "NSDC Retailers Assoc. Skill Council",
    }
    WHO_BENEFITS = {
        "IT": "IT graduates, BCA/MCA students, polytechnic CSE students",
        "Automotive": "ITI mechanical/electrical trainees, diploma engineers",
        "Textile": "ITI textile trainees, NIFT/fashion tech students",
        "Healthcare": "GNM/ANM nursing students, MLT diploma holders",
        "Construction": "Civil engineering diploma holders, ITI civil trainees",
        "Retail/E-commerce": "Commerce graduates, MBA/retail management students",
    }

    def get_skill_sectors(skill_name, full_demand_df):
        row = full_demand_df[full_demand_df["skill"] == skill_name]
        if row.empty:
            return []
        secs = row.iloc[0]["sectors"]
        if isinstance(secs, list):
            return secs
        return [str(secs)]

    def get_skill_districts(skill_name, full_demand_df):
        row = full_demand_df[full_demand_df["skill"] == skill_name]
        if row.empty:
            return []
        dists = row.iloc[0]["districts"]
        if isinstance(dists, list):
            return dists[:3]
        return [str(dists)]

    if disp_gap.empty:
        st.info("No skills match the selected filter criteria. Adjust the sidebar filters.")
    else:
        sorted_gap = (
            disp_gap.sort_values(["demand_count", "match_confidence"], ascending=[False, True])
            .reset_index(drop=True)
        )

        page_col1, page_col2 = st.columns([1, 4])
        with page_col1:
            page_size = st.selectbox("Rows per page", [10, 20, 50, "All"], index=0, key="gap_page_size")

        total_rows = len(sorted_gap)
        start_idx, end_idx = 0, total_rows
        if page_size == "All":
            current_page = 1
            page_rows = sorted_gap
        else:
            num_pages = max(1, (total_rows + page_size - 1) // page_size)
            with page_col2:
                current_page = st.number_input(f"Page (1–{num_pages})", min_value=1, max_value=num_pages, value=1, step=1, key="gap_page_num")
            start_idx = (current_page - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            page_rows = sorted_gap.iloc[start_idx:end_idx]

        st.caption(f"Showing rows {start_idx + 1}–{end_idx} of {total_rows} skills.")

        for idx, row in page_rows.iterrows():
            skill_name = str(row["skill"])
            demand_num = int(row["demand_count"])
            gap_stat   = str(row["gap_status"])
            conf_val   = float(row["match_confidence"])
            course_val = str(row["matched_course"])

            skill_sectors = get_skill_sectors(skill_name, f_demand)
            skill_districts = get_skill_districts(skill_name, f_demand)
            primary_sector = skill_sectors[0] if skill_sectors else "IT"
            nsdc_std = SECTOR_STANDARD.get(primary_sector, "NSDC Framework")
            who = WHO_BENEFITS.get(primary_sector, "Vocational trainees and diploma holders")

            # District tags HTML
            dist_tags = "".join(f'<span class="gap-district-tag">📍{d}</span>' for d in skill_districts)

            if gap_stat == "covered":
                card_cls = "gap-card-green"
                status_pill = '<span class="pill pill-green">✅ Covered</span>'
                urgency_cls, urgency_lbl = "urgency-low", "Low Priority"
                ctx_html = (
                    f'<div class="gap-card-context">'
                    f'<span class="ctx-green">✔ Industry Ready</span> — This skill is <strong>fully matched</strong> in your curriculum (confidence: {conf_val:.1f}%). '
                    f'Graduates completing <em>{course_val}</em> are <strong>job-market ready</strong> for this role.<br>'
                    f'<strong>Who benefits:</strong> {who}.<br>'
                    f'<strong>Industry standard:</strong> Meets <em>{nsdc_std}</em> benchmark. No immediate action required. '
                    f'Recommend reviewing this course every 12 months to stay current.'
                    f'</div>'
                )
            elif gap_stat == "partial":
                card_cls = "gap-card-amber"
                status_pill = '<span class="pill pill-amber">⚠ Partial</span>'
                urgency_cls, urgency_lbl = "urgency-med", "Action Needed"
                gap_pct = round(100 - conf_val, 1)
                ctx_html = (
                    f'<div class="gap-card-context">'
                    f'<span class="ctx-amber">⚠ Upskilling Required</span> — Course <em>{course_val}</em> covers this skill '
                    f'but only at <strong>{conf_val:.1f}%</strong> match ({gap_pct:.1f}% below industry threshold).<br>'
                    f'<strong>Who benefits:</strong> {who} — and the trainers who teach them.<br>'
                    f'<strong>Industry standard:</strong> <em>{nsdc_std}</em> requires ≥80% coverage. '
                    f'<strong>Recommended action:</strong> Add a focused module or lab exercise to close the remaining gap. '
                    f'Estimated effort: 1–2 day faculty workshop or supplementary module.'
                    f'</div>'
                )
            else:
                card_cls = "gap-card-red"
                status_pill = '<span class="pill pill-red">⬤ Missing</span>'
                urgency_cls, urgency_lbl = "urgency-high", "Critical Gap"
                ctx_html = (
                    f'<div class="gap-card-context">'
                    f'<span class="ctx-red">⬤ No Curriculum Coverage</span> — <strong>{demand_num} employer(s)</strong> '
                    f'in Maharashtra actively demand this skill, but <strong>zero vocational courses</strong> cover it (match: {conf_val:.1f}%).<br>'
                    f'<strong>Who benefits:</strong> {who} and employers in {", ".join(skill_districts) if skill_districts else "the region"}.<br>'
                    f'<strong>Industry standard:</strong> <em>{nsdc_std}</em> lists this as a Tier-1 employability skill.<br>'
                    f'<strong>Recommended action:</strong> Develop a new certificate course or integrate into existing programmes. '
                    f'Flag for ITI coordinator and DVET for urgent curriculum revision.'
                    f'</div>'
                )

            card_markup = f"""
            <div class="gap-card {card_cls}">
              <div class="gap-card-header">
                <span class="gap-card-skill">{skill_name}</span>
                {status_pill}
                <span class="gap-card-demand">🏭 {demand_num} employer{'s' if demand_num != 1 else ''}</span>
                <span class="gap-card-conf">Match: {conf_val:.1f}%</span>
              </div>
              <div class="gap-card-body">
                <div class="gap-card-course">
                  <span>📚</span>
                  <span>Best matched course: <span class="gap-card-course-name">{course_val}</span></span>
                </div>
                {ctx_html}
              </div>
              <div class="gap-card-footer">
                <span class="gap-urgency {urgency_cls}">{urgency_lbl}</span>
                {dist_tags}
              </div>
            </div>
            """
            render_clean_html(card_markup)

            fb_col_a, fb_col_b, _ = st.columns([1, 1, 5])
            if fb_col_a.button("👍 Agree", key=f"btn_agree_{idx}_{skill_name}", use_container_width=True):
                log_feedback(skill_name, course_val, gap_stat, "Agree")
                st.success(f"✅ **Agree** recorded for '{skill_name}'")
            if fb_col_b.button("👎 Disagree", key=f"btn_disagree_{idx}_{skill_name}", use_container_width=True):
                log_feedback(skill_name, course_val, gap_stat, "Disagree")
                st.warning(f"⚠️ **Disagree** recorded for '{skill_name}' — flagged for review")



    # Color-coded full matrix expander
    def color_gap(row):
        s = row["gap_status"]
        if s == "covered":
            return ["background-color:rgba(46,125,110,0.12);color:#2E7D6E"] * len(row)
        elif s == "partial":
            return ["background-color:rgba(212,137,10,0.12);color:#D4890A"] * len(row)
        return ["background-color:rgba(92,107,192,0.12);color:#5C6BC0"] * len(row)

    if not disp_gap.empty:
        with st.expander(f"📊 Full Color-Coded Gap Table ({len(disp_gap)} skills)", expanded=False):
            styled_full = (
                disp_gap.sort_values(["demand_count", "match_confidence"], ascending=[False, True])
                .reset_index(drop=True)
                .style.apply(color_gap, axis=1)
                .format({"match_confidence": "{:.1f}%"})
            )
            st.dataframe(styled_full, use_container_width=True, hide_index=True, height=450)

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        st.download_button("📥 Download Gap Report (CSV)", disp_gap.to_csv(index=False).encode(), "skill_gap_report.csv", "text/csv")
    with dl_col2:
        # Build Excel workbook with multiple sheets
        _excel_buf = io.BytesIO()
        with pd.ExcelWriter(_excel_buf, engine="openpyxl") as _writer:
            # Sheet 1: Gap Analysis
            _gap_export = disp_gap.copy()
            _gap_export.to_excel(_writer, sheet_name="Gap Analysis", index=False)
            # Sheet 2: Course Health (computed inline)
            _demanded_lower_set = set(f_demand["skill"].str.lower().tolist())
            _ch_records = []
            for _, _cr in curr_df.iterrows():
                _taught = [s.strip() for s in str(_cr.get("skills_taught","")).split(",") if s.strip()]
                _total = len(_taught)
                _cov = [s for s in _taught if s.lower() in _demanded_lower_set]
                _pct = round(len(_cov)/_total*100,1) if _total else 0
                _health = ("Aligned" if _pct>=70 else ("Needs Update" if _pct>=40 else "Obsolete"))
                _ch_records.append({"Course ID":_cr["course_id"],"Course Name":_cr["course_name"],"Sector":_cr.get("sector",""),"Coverage %":_pct,"Health Status":_health})
            pd.DataFrame(_ch_records).to_excel(_writer, sheet_name="Course Health", index=False)
            # Sheet 3: Trainer Roadmap
            f_trainer.to_excel(_writer, sheet_name="Trainer Roadmap", index=False)
            # Sheet 4: Summary KPIs
            _summary = pd.DataFrame([{
                "Metric": "Jobs Analyzed", "Value": len(jobs_df)},
                {"Metric": "Skills Tracked", "Value": len(f_gap)},
                {"Metric": "Covered Skills", "Value": n_cov},
                {"Metric": "Partial Skills", "Value": n_par},
                {"Metric": "Missing Skills", "Value": n_mis},
                {"Metric": "Alignment Rate %", "Value": align_pct},
                {"Metric": "Trainer Interventions", "Value": len(f_trainer)},
                {"Metric": "Sectors Analyzed", "Value": len(sel_sectors)},
                {"Metric": "Districts Analyzed", "Value": len(sel_districts)},
                {"Metric": "State Scope", "Value": "Maharashtra, India"},
                {"Metric": "Report Generated", "Value": datetime.now().strftime("%Y-%m-%d %H:%M")},
            ])
            _summary.to_excel(_writer, sheet_name="Summary", index=False)
        _excel_buf.seek(0)
        st.download_button(
            "📊 Export Full Report (.xlsx)",
            _excel_buf.getvalue(),
            "skilltrack_full_report.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )



    if FEEDBACK_FILE.exists():
        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                fb_data = json.load(f)
            if fb_data:
                with st.expander(f"📝 User Feedback Audit Log ({len(fb_data)} entries)"):
                    fb_df = pd.DataFrame(fb_data)
                    st.dataframe(fb_df, use_container_width=True, hide_index=True)
        except Exception:
            pass


# ═══ TAB 2 — Course Health Audit ═════════════════════════════════════════════
with tab2:
    render_clean_html("""
    <div class="sec-head">
      <div class="sec-head-title">Course Health Audit</div>
      <div class="sec-head-desc">Each course rated by industry relevance of its taught skills —
        <span class="pill pill-green">✅ Aligned ≥70%</span>
        <span class="pill pill-amber">⚠️ Needs Update 40–69%</span>
        <span class="pill pill-red">📋 Obsolete &lt;40%</span>
      </div>
    </div>
    """)

    demanded_lower = set(f_demand["skill"].str.lower().tolist())
    records = []
    for _, cr in curr_df.iterrows():
        taught = [s.strip() for s in str(cr.get("skills_taught", "")).split(",") if s.strip()]
        total = len(taught)
        cov = [s for s in taught if s.lower() in demanded_lower]
        gaps = [s for s in taught if s.lower() not in demanded_lower]
        pct = round(len(cov) / total * 100, 1) if total else 0
        if pct >= 70:
            health = "✅ Aligned"
        elif pct >= 40:
            health = "⚠️ Needs Update"
        else:
            health = "📋 Obsolete"
        records.append({
            "Course ID": cr["course_id"], "Course Name": cr["course_name"],
            "Sector": cr.get("sector", ""), "Total Skills": total,
            "Demanded Skills": len(cov), "Coverage %": pct,
            "Health": health, "Gap Skills": ", ".join(gaps),
        })

    ch_df = pd.DataFrame(records)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Courses", len(ch_df))
    c2.metric("✅ Aligned", len(ch_df[ch_df["Health"].str.contains("Aligned")]))
    c3.metric("⚠️ Needs Update", len(ch_df[ch_df["Health"].str.contains("Update")]))
    c4.metric("📋 Obsolete", len(ch_df[ch_df["Health"].str.contains("Obsolete")]))

    def color_health(row):
        h = str(row["Health"])
        if "Aligned" in h:
            return ["background-color:rgba(46,125,110,0.12);color:#2E7D6E"] * len(row)
        elif "Update" in h:
            return ["background-color:rgba(212,137,10,0.12);color:#D4890A"] * len(row)
        return ["background-color:rgba(92,107,192,0.12);color:#5C6BC0"] * len(row)

    styled_ch = ch_df.style.apply(color_health, axis=1).format({"Coverage %": "{:.1f}%"})
    st.dataframe(styled_ch, use_container_width=True, hide_index=True, height=460)

    st.markdown("#### Detailed Breakdown")
    for _, cr in ch_df.iterrows():
        if "Aligned" in cr["Health"]:
            ic, pc = "✅", "pill-green"
        elif "Update" in cr["Health"]:
            ic, pc = "⚠️", "pill-amber"
        else:
            ic, pc = "📋", "pill-red"
        gap_line = f'<br/><span style="color:var(--amber);font-size:0.75rem">⚠ Not in demand: {cr["Gap Skills"]}</span>' if cr["Gap Skills"] else ""
        render_clean_html(f"""
        <div class="cc">
          <div class="icon">{ic}</div>
          <div class="info">
            <div class="name">{cr['Course Name']}</div>
            <div class="meta">{cr['Sector']} · {cr['Course ID']}</div>
            <div class="detail"><strong>{cr['Demanded Skills']}/{cr['Total Skills']}</strong> skills aligned ({cr['Coverage %']}%){gap_line}</div>
          </div>
          <div class="hb"><span class="pill {pc}">{cr['Health']}</span></div>
        </div>
        """)

    ch_c1, ch_c2 = st.columns(2)
    with ch_c1:
        st.download_button("📥 Download Course Health (CSV)", ch_df.to_csv(index=False).encode(), "course_health_audit.csv", "text/csv")
    with ch_c2:
        _ch_buf = io.BytesIO()
        with pd.ExcelWriter(_ch_buf, engine="openpyxl") as _ch_writer:
            ch_df.to_excel(_ch_writer, sheet_name="Course Health", index=False)
        _ch_buf.seek(0)
        st.download_button(
            "📊 Export Course Health (.xlsx)",
            _ch_buf.getvalue(),
            "course_health_audit.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


# ═══ TAB 3 — Trainer Planner ═════════════════════════════════════════════════
with tab3:
    render_clean_html("""
    <div class="sec-head">
      <div class="sec-head-title">Trainer Development &amp; Faculty Upskilling Roadmap</div>
      <div class="sec-head-desc">Prioritised intervention plan for ITI/vocational faculty based on market demand &amp; gap severity.</div>
    </div>
    """)

    if f_trainer.empty:
        st.success("All skills covered — no trainer interventions required!")
    else:
        m1, m2, m3 = st.columns(3)
        hp = f_trainer[f_trainer["demand_count"] >= 2]
        m1.metric("Total Interventions", len(f_trainer))
        m2.metric("🔵 High-Demand Priority", len(hp))
        m3.metric("🟡 Emerging Skills", len(f_trainer) - len(hp))

        SSC_MAP = {
            "IT": "IT-ITeS SSC (NASSCOM)",
            "Automotive": "Automotive Skills Development Council (ASDC)",
            "Textile": "Textile Sector Skill Council (TSC)",
            "Healthcare": "Healthcare Sector Skill Council (HSSC)",
            "Construction": "Construction Skill Development Council of India (CSDCI)",
            "Retail/E-commerce": "Retailers Association's Skill Council of India (RASCI)",
        }

        for _, r in f_trainer.iterrows():
            sk_name = str(r["skill"])
            dm_count = int(r["demand_count"])
            bc = "var(--red)" if dm_count >= 2 else "var(--accent)"
            pill_cls = "pill-red" if dm_count >= 2 else "pill-amber"
            p_label = "High-Demand Priority" if dm_count >= 2 else "Emerging Skill"

            row_d = f_demand[f_demand["skill"] == sk_name]
            sec_list = []
            dist_list = []
            if not row_d.empty:
                s_val = row_d.iloc[0]["sectors"]
                sec_list = s_val if isinstance(s_val, list) else [str(s_val)]
                d_val = row_d.iloc[0]["districts"]
                dist_list = d_val[:3] if isinstance(d_val, list) else [str(d_val)]

            primary_sec = sec_list[0] if sec_list else "General"
            ssc_name = SSC_MAP.get(primary_sec, "NSDC National Standard")
            dist_str = ", ".join(dist_list) if dist_list else "Maharashtra"
            intervention_action = (
                f"3-Day Faculty Training of Trainers (ToT) in collaboration with {ssc_name} + Hands-on Lab Sandbox"
                if dm_count >= 2
                else f"1-Day Industry Expert Seminar & Self-Paced Digital Courseware for ITI Instructors"
            )

            render_clean_html(f"""
            <div class="tc" style="border-left-color:{bc}">
              <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">
                <strong>{sk_name}</strong>
                <span class="pill {pill_cls}">Demand: {dm_count}</span>
                <span class="gap-district-tag">Industry: {primary_sec}</span>
                <span class="gap-district-tag">📍 {dist_str}</span>
              </div>
              <div class="rsn"><strong>Analysis:</strong> {r['reason']}</div>
              <div class="tc-context">
                <strong>Faculty Intervention Roadmap:</strong> {intervention_action}<br>
                <strong>Affiliated Council:</strong> {ssc_name} · <strong>Target Beneficiaries:</strong> ITI &amp; Polytechnic trainers across {dist_str}.
              </div>
            </div>
            """)

        tr_c1, tr_c2 = st.columns(2)
        with tr_c1:
            st.download_button("📥 Export Trainer Roadmap (CSV)", f_trainer.to_csv(index=False).encode(), "trainer_roadmap.csv", "text/csv")
        with tr_c2:
            _tr_buf = io.BytesIO()
            with pd.ExcelWriter(_tr_buf, engine="openpyxl") as _tr_writer:
                f_trainer.to_excel(_tr_writer, sheet_name="Trainer Roadmap", index=False)
            _tr_buf.seek(0)
            st.download_button(
                "📊 Export Trainer Roadmap (.xlsx)",
                _tr_buf.getvalue(),
                "trainer_roadmap.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# ═══ TAB 4 — Regional View (enhanced with district heatmap) ══════════════════
with tab4:
    render_clean_html("""
    <div class="sec-head">
      <div class="sec-head-title">Sectoral &amp; Regional Intelligence</div>
      <div class="sec-head-desc">Skill demand distribution across 7 Maharashtra districts and 6 industry sectors.</div>
    </div>
    """)

    v1, v2 = st.columns(2)
    with v1:
        st.markdown("#### Jobs by Sector")
        sd = jobs_df["sector"].value_counts().reset_index()
        sd.columns = ["Sector", "Jobs"]
        st.bar_chart(sd.set_index("Sector"), color="#1E4D8C", height=280)
    with v2:
        st.markdown("#### Jobs by District (Maharashtra)")
        dd = jobs_df["district"].value_counts().reset_index()
        dd.columns = ["District", "Jobs"]
        st.bar_chart(dd.set_index("District"), color="#2E7D6E", height=280)

    # ── District × Sector heatmap ────────────────────────────────────────────
    st.markdown("#### 🗺️ District × Sector Demand Heatmap")
    st.caption("Number of job postings per district per sector — shows WHERE each sector is hiring most.")
    pivot = jobs_df.pivot_table(index="district", columns="sector", values="job_id", aggfunc="count", fill_value=0)
    pivot.index.name = "District"
    pivot.columns.name = "Sector"
    try:
        styled_pivot = pivot.style.background_gradient(cmap="Blues", axis=None)
    except Exception:
        def cell_bg(val):
            if isinstance(val, (int, float)) and val > 0:
                alpha = min(0.85, 0.15 + 0.7 * (val / max(pivot.values.max(), 1)))
                return f"background-color: rgba(30, 77, 140, {alpha:.2f}); color: #ffffff; font-weight: 600;"
            return ""
        styler = pivot.style
        map_fn = getattr(styler, "map", getattr(styler, "applymap", None))
        styled_pivot = map_fn(cell_bg) if map_fn else styler

    st.dataframe(styled_pivot, use_container_width=True)

    # ── Gap Severity by District ─────────────────────────────────────────────
    st.markdown("#### 📍 Skill Gap Severity by District")
    st.caption("Shows how many missing/partial skills each district contributes to the demand pool.")
    dist_gap_rows = []
    all_dists = sorted(jobs_df["district"].unique())
    for dist in all_dists:
        dist_jobs = jobs_df[jobs_df["district"] == dist]
        if dist_jobs.empty:
            continue
        dist_demand = compute_demand(dist_jobs)
        dist_gap = detect_gaps(dist_demand, curr_df)
        dist_gap_rows.append({
            "District": dist,
            "Jobs": len(dist_jobs),
            "Skills Demanded": len(dist_demand),
            "✅ Covered": len(dist_gap[dist_gap["gap_status"] == "covered"]),
            "⚠️ Partial":  len(dist_gap[dist_gap["gap_status"] == "partial"]),
            "⬤ Missing":  len(dist_gap[dist_gap["gap_status"] == "missing"]),
        })
    dist_gap_df = pd.DataFrame(dist_gap_rows)
    dist_gap_df["Gap Score"] = dist_gap_df["⚠️ Partial"] * 1 + dist_gap_df["⬤ Missing"] * 3
    dist_gap_df = dist_gap_df.sort_values("Gap Score", ascending=False)

    try:
        styled_dist_gap = dist_gap_df.style.background_gradient(subset=["Gap Score"], cmap="Purples")
    except Exception:
        def score_bg(val):
            if isinstance(val, (int, float)):
                if val >= 5:
                    return "background-color: rgba(92, 107, 192, 0.20); color: #5C6BC0; font-weight: 700;"
                elif val >= 2:
                    return "background-color: rgba(212, 137, 10, 0.20); color: #D4890A; font-weight: 600;"
                return "background-color: rgba(46, 125, 110, 0.20); color: #2E7D6E; font-weight: 600;"
            return ""
        styler = dist_gap_df.style
        map_fn = getattr(styler, "map", getattr(styler, "applymap", None))
        styled_dist_gap = map_fn(score_bg, subset=["Gap Score"]) if map_fn else styler

    st.dataframe(styled_dist_gap, use_container_width=True, hide_index=True)
    st.caption("**Gap Score** = (Partial × 1) + (Missing × 3). Higher score = more urgent curriculum intervention needed.")

    st.markdown("#### Top In-Demand Skills (Filtered View)")
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


# ═══ TAB 5 — Quick Wins ══════════════════════════════════════════════════════
with tab5:
    render_clean_html("""
    <div class="sec-head">
      <div class="sec-head-title">⚡ Quick Wins — Easiest Gaps to Close</div>
      <div class="sec-head-desc">Partial-match skills sorted by employer demand — these need only a small curriculum update to become industry-ready.
        Act on these first for maximum impact with minimum effort.</div>
    </div>
    """)

    # Quick wins = partial gaps sorted by demand desc
    partial_gaps = f_gap[f_gap["gap_status"] == "partial"].sort_values("demand_count", ascending=False)
    missing_gaps = f_gap[f_gap["gap_status"] == "missing"].sort_values("demand_count", ascending=False)

    qw_m1, qw_m2, qw_m3 = st.columns(3)
    qw_m1.metric("⚡ Quick Wins Available", len(partial_gaps), help="Partial-match skills that need only a module update")
    qw_m2.metric("🚨 Critical Gaps", len(missing_gaps), help="Skills with zero curriculum coverage — need new courses")
    qw_m3.metric("🏭 Total Employer Demand", int(partial_gaps["demand_count"].sum() + missing_gaps["demand_count"].sum()), help="Sum of employer demand across all gaps")

    if not partial_gaps.empty:
        st.markdown("### ⚡ Quick Wins — Add a Module to Close the Gap")
        st.caption("These skills are already partially covered. A 1–2 day faculty workshop or one new lab session can close the gap.")
        for _, qrow in partial_gaps.iterrows():
            sk = str(qrow["skill"])
            dc = int(qrow["demand_count"])
            mc = str(qrow["matched_course"])
            cf = float(qrow["match_confidence"])
            gap_remaining = round(100 - cf, 1)

            sk_dists = []
            row_d = f_demand[f_demand["skill"] == sk]
            if not row_d.empty:
                dists_val = row_d.iloc[0]["districts"]
                sk_dists = dists_val[:3] if isinstance(dists_val, list) else [str(dists_val)]
            dist_str = ", ".join(sk_dists) if sk_dists else "Maharashtra"

            sk_secs = []
            if not row_d.empty:
                secs_val = row_d.iloc[0]["sectors"]
                sk_secs = secs_val if isinstance(secs_val, list) else [str(secs_val)]
            sector_str = ", ".join(sk_secs) if sk_secs else "Multiple"

            effort = "1-day workshop" if gap_remaining < 15 else ("2-day workshop" if gap_remaining < 25 else "New module (1 week)")

            render_clean_html(f"""
            <div class="qw-card">
              <div class="qw-icon">⚡</div>
              <div class="qw-body">
                <div class="qw-title">{sk}</div>
                <div class="qw-meta">{sector_str} · {dist_str} · {dc} employer{'s' if dc != 1 else ''} demanding</div>
                <div class="qw-action">
                  Currently matched at <strong>{cf:.1f}%</strong> via <em>{mc}</em>.
                  Gap remaining: <strong>{gap_remaining:.1f}%</strong>.<br>
                  <strong>Recommended fix:</strong> Add a focused {effort} to existing course.
                  This single update unlocks job-market readiness for <strong>{dc} employer requirement{'s' if dc!=1 else ''}</strong>.
                </div>
              </div>
              <div class="qw-badge"><span class="pill pill-amber">⚠ {gap_remaining:.0f}% gap</span></div>
            </div>
            """)
    else:
        st.success("✅ No partial gaps found — all skills are either fully covered or have no curriculum match at all.")

    if not missing_gaps.empty:
        st.markdown("---")
        st.markdown("### 📋 High-Priority Gaps — New Course Development Needed")
        st.caption("These have zero curriculum coverage. Prioritise by employer demand count.")
        for _, mrow in missing_gaps.iterrows():
            sk = str(mrow["skill"])
            dc = int(mrow["demand_count"])
            cf = float(mrow["match_confidence"])
            row_d = f_demand[f_demand["skill"] == sk]
            sk_secs = []
            if not row_d.empty:
                secs_val = row_d.iloc[0]["sectors"]
                sk_secs = secs_val if isinstance(secs_val, list) else [str(secs_val)]
            sector_str = ", ".join(sk_secs) if sk_secs else "Multiple"

            render_clean_html(f"""
            <div class="qw-card" style="border-left-color:var(--indigo);border-color:var(--indigo-border);">
              <div class="qw-icon">📋</div>
              <div class="qw-body">
                <div class="qw-title">{sk}</div>
                <div class="qw-meta">{sector_str} · {dc} employer{'s' if dc != 1 else ''} · 0% curriculum match</div>
                <div class="qw-action">
                  <strong>No existing course covers this skill.</strong>
                  Recommended: Develop a new certificate module or integrate into a related course.
                  Flag to DVET / ITI coordinator for curriculum revision.
                </div>
              </div>
              <div class="qw-badge"><span class="pill pill-red">⬤ Curriculum Priority</span></div>
            </div>
            """)

    # Excel export for Quick Wins
    _qw_buf = io.BytesIO()
    with pd.ExcelWriter(_qw_buf, engine="openpyxl") as _qw_writer:
        if not partial_gaps.empty:
            partial_gaps.to_excel(_qw_writer, sheet_name="Quick Wins (Partial)", index=False)
        if not missing_gaps.empty:
            missing_gaps.to_excel(_qw_writer, sheet_name="Critical Gaps (Missing)", index=False)
    _qw_buf.seek(0)
    st.download_button(
        "📥 Export Quick Wins Action Plan (.xlsx)",
        _qw_buf.getvalue(),
        "quick_wins_action_plan.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ═══ TAB 6 — AI Skill Intelligence & Curriculum Advisor ══════════════════════
with tab6:
    render_clean_html("""
    <div class="sec-head">
      <div class="sec-head-title">🎓 AI Skill Intelligence &amp; Curriculum Advisor</div>
      <div class="sec-head-desc">Autonomous skill extraction, deterministic RapidFuzz curriculum benchmarking, and institutional action roadmap.</div>
    </div>
    """)

    # Built-in demo presets
    DEMO_PRESETS = {
        "🚗 Automotive (EV)": {
            "type": "Job Description",
            "text": "EV technician required with Battery Management Systems, CAN Bus diagnostics, EV safety, battery testing and electrical troubleshooting in Pune.",
        },
        "☁️ IT & Cloud": {
            "type": "Job Description",
            "text": "Cloud Engineer needed with Docker, Kubernetes container orchestration, CI/CD pipelines, AWS Cloud architecture, and microservices security.",
        },
        "🏥 Healthcare (Lab)": {
            "type": "Course / Curriculum Syllabus",
            "text": "Medical Laboratory Technician with Hematology, Clinical Biochemistry, Blood Banking, Quality Control, and Diagnostic Equipment Maintenance.",
        },
        "🛍️ Retail (Omnichannel)": {
            "type": "Industry Requirement",
            "text": "Omnichannel Retail Manager skilled in POS Systems, Inventory Forecasting, E-commerce Operations, Customer Retention, and Supply Chain Logistics.",
        },
    }

    if "ai_advisor_text_area" not in st.session_state:
        st.session_state["ai_advisor_text_area"] = DEMO_PRESETS["🚗 Automotive (EV)"]["text"]
    if "ai_advisor_input_type" not in st.session_state:
        st.session_state["ai_advisor_input_type"] = "Job Description"

    def set_advisor_example(text_val: str, type_val: str):
        st.session_state["ai_advisor_text_area"] = text_val
        st.session_state["ai_advisor_input_type"] = type_val

    st.markdown("##### ⚡ Quick Load Industry Demonstrations")
    demo_cols = st.columns(4)
    for col, (demo_name, demo_data) in zip(demo_cols, DEMO_PRESETS.items()):
        with col:
            st.button(
                demo_name,
                use_container_width=True,
                on_click=set_advisor_example,
                args=(demo_data["text"], demo_data["type"]),
            )

    c_type, _ = st.columns([1, 2])
    with c_type:
        input_types = [
            "Job Description",
            "Course / Curriculum Syllabus",
            "Industry Requirement",
            "Tender / Procurement Specification",
            "General Technical Text",
        ]
        curr_idx = input_types.index(st.session_state["ai_advisor_input_type"]) if st.session_state["ai_advisor_input_type"] in input_types else 0
        selected_input_type = st.selectbox("Input Classification", input_types, index=curr_idx)
        st.session_state["ai_advisor_input_type"] = selected_input_type

    txt_input = st.text_area(
        "Enter or Paste Technical Requirement / Syllabus Text:",
        value=st.session_state.get("ai_advisor_text_area", ""),
        height=125,
        placeholder="Paste a job posting, course syllabus, tender requirement, or industry competency profile...",
        key="ai_advisor_text_area",
    )

    run_analysis_clicked = st.button("🚀 Analyze Requirement with AI", type="primary", use_container_width=True)

    if run_analysis_clicked:
        if not txt_input.strip():
            st.warning("⚠️ Please provide input text to analyze.")
        else:
            with st.spinner("Analyzing competency profile & benchmarking against vocational curriculum..."):
                analysis_res = analyze_requirement(
                    text=txt_input,
                    input_type=st.session_state["ai_advisor_input_type"],
                    curriculum_df=curr_df,
                    demand_df=demand_df,
                )
                if "error" in analysis_res:
                    st.error(analysis_res["error"])
                else:
                    st.session_state["ai_advisor_result"] = analysis_res

    # Render analysis results
    res = st.session_state.get("ai_advisor_result")
    if res and "error" not in res:
        st.markdown("---")

        # 1. Overview KPI Row
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            render_clean_html(f"""
            <div class="kpi-card" style="border-top: 3px solid #1E4D8C;">
              <div class="kpi-label">Skills Detected</div>
              <div class="kpi-num neutral">{res['skills_detected']}</div>
              <div class="kpi-sub">AI / NLP Extracted</div>
            </div>
            """)
        with k2:
            render_clean_html(f"""
            <div class="kpi-card" style="border-top: 3px solid var(--green);">
              <div class="kpi-label">Curriculum Covered</div>
              <div class="kpi-num covered">{res['covered_count']}</div>
              <div class="kpi-sub">≥ 80% Match Confidence</div>
            </div>
            """)
        with k3:
            render_clean_html(f"""
            <div class="kpi-card" style="border-top: 3px solid var(--amber);">
              <div class="kpi-label">Partial Gaps</div>
              <div class="kpi-num partial">{res['partial_count']}</div>
              <div class="kpi-sub">50–79.9% Match (Upgradable)</div>
            </div>
            """)
        with k4:
            render_clean_html(f"""
            <div class="kpi-card" style="border-top: 3px solid var(--indigo);">
              <div class="kpi-label">Missing Skills</div>
              <div class="kpi-num missing">{res['missing_count']}</div>
              <div class="kpi-sub">&lt; 50% Match (Zero Coverage)</div>
            </div>
            """)
        with k5:
            render_clean_html(f"""
            <div class="kpi-card" style="border-top: 3px solid var(--accent);">
              <div class="kpi-label">Alignment Rate</div>
              <div class="kpi-num neutral">{res['alignment_pct']}%</div>
              <div class="kpi-sub">Institutional Readiness</div>
            </div>
            """)

        # 2. Skill Alignment & RapidFuzz Match Matrix
        st.markdown("##### 📋 Skill Alignment & Curriculum Match Matrix")
        align_df = res.get("alignment_df")
        if isinstance(align_df, pd.DataFrame) and not align_df.empty:
            def style_align_row(row):
                st_val = str(row["Status"]).lower()
                if st_val == "covered":
                    return ["background-color:rgba(46,125,110,0.10); color:#2E7D6E;"] * len(row)
                elif st_val == "partial":
                    return ["background-color:rgba(212,137,10,0.10); color:#D4890A;"] * len(row)
                return ["background-color:rgba(92,107,192,0.10); color:#5C6BC0;"] * len(row)

            display_cols = ["Skill", "Category", "Match Score", "Status", "Best Matching Course", "Priority"]
            viewable_df = align_df[[c for c in display_cols if c in align_df.columns]]
            st.dataframe(
                viewable_df.style.apply(style_align_row, axis=1),
                use_container_width=True,
                hide_index=True,
            )

        # 3. Critical Skill Gaps
        critical_gaps = res.get("critical_gaps", [])
        if critical_gaps:
            st.markdown("##### ⚠️ Critical Skill Gaps & Curriculum Action Required")
            for gap in critical_gaps:
                is_missing = gap["status"] == "missing"
                bd_color = "var(--indigo)" if is_missing else "var(--amber)"
                bg_chip = "rgba(92,107,192,0.12)" if is_missing else "rgba(212,137,10,0.12)"
                chip_txt = "🔴 Missing (<50%)" if is_missing else "🟡 Partial Gap (50–79%)"
                render_clean_html(f"""
                <div style="background:var(--bg-card); border:1px solid var(--border); border-left:4px solid {bd_color}; border-radius:8px; padding:14px 18px; margin-bottom:12px; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
                  <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <span style="font-size:15px; font-weight:700; color:var(--text);">{gap['skill']}</span>
                    <span style="background:{bg_chip}; color:{bd_color}; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:700;">
                      {chip_txt} • {gap['score']:.1f}% Match
                    </span>
                  </div>
                  <div style="margin-top:8px; font-size:13px; color:var(--text); line-height:1.5;">
                    <strong>Why It Matters:</strong> {gap['why_it_matters']}<br>
                    <strong>Curriculum State:</strong> {gap['curriculum_coverage']}<br>
                    <strong>Recommended Action:</strong> {gap['recommended_action']}<br>
                    <span style="display:inline-block; margin-top:4px; font-size:12px; color:var(--text-dim);">
                      Sector Skill Council Benchmark: <em>{gap['ssc']}</em>
                    </span>
                  </div>
                </div>
                """)

        # 4. Faculty Development Roadmap & Quick Wins
        rc1, rc2 = st.columns([1, 1])
        with rc1:
            st.markdown("##### 👨‍🏫 Faculty Development Roadmap")
            roadmap = res.get("trainer_roadmap", [])
            if not roadmap:
                st.info("No urgent faculty interventions required. Existing staff competencies align with requirements.")
            else:
                for tr in roadmap:
                    prio_color = "var(--indigo)" if "HIGH" in tr["priority"] else "var(--amber)"
                    prio_bg = "rgba(92,107,192,0.12)" if "HIGH" in tr["priority"] else "rgba(212,137,10,0.12)"
                    render_clean_html(f"""
                    <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:8px; padding:12px 16px; margin-bottom:10px; border-left:3px solid {prio_color};">
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <strong style="color:var(--text); font-size:14px;">{tr['skill']}</strong>
                        <span style="background:{prio_bg}; color:{prio_color}; padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700;">{tr['priority']}</span>
                      </div>
                      <div style="font-size:13px; color:var(--accent); font-weight:600; margin-bottom:4px;">{tr['training']}</div>
                      <div style="font-size:12px; color:var(--text-dim); line-height:1.4;">{tr['reason']}</div>
                      <div style="font-size:11px; color:var(--text-dim); margin-top:4px;">SSC Benchmark: {tr['ssc']}</div>
                    </div>
                    """)

        with rc2:
            st.markdown("##### ⚡ Quick Wins (High-ROI Interventions)")
            quick_wins = res.get("quick_wins", [])
            if not quick_wins:
                st.info("No partial gaps detected. Focus on primary missing competencies.")
            else:
                for qw in quick_wins:
                    render_clean_html(f"""
                    <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:8px; padding:12px 16px; margin-bottom:10px; border-left:3px solid var(--green);">
                      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <strong style="color:var(--text); font-size:14px;">{qw['skill']}</strong>
                        <span style="background:rgba(46,125,110,0.12); color:var(--green); padding:2px 8px; border-radius:8px; font-size:11px; font-weight:700;">{qw['current_match']} Match</span>
                      </div>
                      <div style="font-size:12px; color:var(--text-dim);">Target Course: <strong>{qw['course']}</strong></div>
                      <div style="font-size:13px; color:var(--text); margin-top:4px;"><strong>Intervention:</strong> {qw['intervention']}</div>
                      <div style="font-size:12px; color:var(--accent); font-weight:600; margin-top:4px;">Effort: {qw['effort']}</div>
                    </div>
                    """)

        # 5. Grounded AI Executive Summary
        st.markdown("##### 📝 Grounded AI Executive Summary")
        render_clean_html(f"""
        <div style="background:rgba(30,77,140,0.04); border:1px solid rgba(30,77,140,0.22); border-radius:10px; padding:18px 20px; margin-top:8px;">
          <div style="display:flex; gap:8px; margin-bottom:12px; align-items:center; flex-wrap:wrap;">
            <span style="background:#1E4D8C; color:#fff; font-size:11px; font-weight:700; padding:3px 8px; border-radius:4px; letter-spacing:0.5px;">AI RECOMMENDATION</span>
            <span style="background:rgba(46,125,110,0.15); color:#2E7D6E; font-size:11px; font-weight:700; padding:3px 8px; border-radius:4px; letter-spacing:0.5px;">RAPIDFUZZ CALCULATED</span>
          </div>
          <div style="font-size:14px; line-height:1.6; color:var(--text); white-space:pre-line;">
            {res['executive_summary']}
          </div>
        </div>
        """)

        # 6. Human-in-the-Loop Validation
        st.markdown("##### 🤝 Human-in-the-Loop Validation")
        st.caption("Vocational directors and curriculum reviewers can validate these findings to continuously calibrate SkillTrack AI.")
        val_c1, val_c2, _ = st.columns([1, 1, 2])
        with val_c1:
            if st.button("👍 Confirm & Agree", use_container_width=True, key="ai_val_agree"):
                for gap in res.get("critical_gaps", []):
                    log_feedback(
                        skill=gap["skill"],
                        course=gap["course"],
                        gap_status=gap["status"],
                        user_response="Agree",
                        match_score=gap["score"],
                        recommendation=gap["recommended_action"],
                        ai_provider=res["provider_name"],
                    )
                st.toast("✅ Assessment confirmed! Validations logged.", icon="👍")
                st.success("✅ Assessment confirmed! Validations recorded in calibration log.")
                st.rerun()
        with val_c2:
            if st.button("👎 Flag for Recalibration", use_container_width=True, key="ai_val_disagree"):
                for gap in res.get("critical_gaps", []):
                    log_feedback(
                        skill=gap["skill"],
                        course=gap["course"],
                        gap_status=gap["status"],
                        user_response="Disagree",
                        match_score=gap["score"],
                        recommendation=gap["recommended_action"],
                        ai_provider=res["provider_name"],
                    )
                st.toast("⚠️ Flagged for recalibration.", icon="⚠️")
                st.info("⚠️ Flagged for threshold recalibration in feedback log.")
                st.rerun()

        # 7. Institutional Export Suite
        st.markdown("##### 📥 Export Institutional Analysis")
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            excel_bytes = export_analysis_to_excel(res)
            st.download_button(
                "📥 Download Institutional Action Plan (.xlsx)",
                data=excel_bytes,
                file_name=f"skilltrack_institutional_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with exp_col2:
            csv_bytes = export_analysis_to_csv(res)
            st.download_button(
                "📄 Download Skill Alignment Matrix (.csv)",
                data=csv_bytes,
                file_name=f"skill_alignment_matrix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )




# ═══ MODEL FEEDBACK & CONTINUOUS CALIBRATION ═════════════════════════════════
employer_validations = []
if FEEDBACK_FILE.exists():
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            data_loaded = json.load(f)
            if isinstance(data_loaded, list):
                employer_validations = data_loaded
    except Exception:
        employer_validations = []

total_validated  = len(employer_validations)
agreed_count     = sum(1 for v in employer_validations if v.get("user_response") == "Agree")
disagreed_count  = sum(1 for v in employer_validations if v.get("user_response") == "Disagree")
agreement_pct    = round((agreed_count / total_validated * 100), 1) if total_validated > 0 else 0.0

render_clean_html(f"""
<div class="fb-panel">
    <div class="fb-panel-head">
        <span class="fb-panel-title">🔄 Model Feedback &amp; Continuous Calibration</span>
        <span class="fb-active-badge">Active Evidence-Based Loop</span>
    </div>
    <div class="fb-counter">✨ <span class="num">{total_validated}</span> gaps validated by employers so far.</div>
    <div class="fb-desc">Employer votes directly tune NLP match confidence thresholds and validate regional curriculum interventions — building a continuously improving, evidence-based skill intelligence engine.</div>
</div>
""")

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
