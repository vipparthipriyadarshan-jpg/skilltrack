import os
import re
import json
import socket
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

# Force IPv4 socket resolution on Windows to avoid WinError 10065
try:
    import urllib3.util.connection as urllib3_cn
    urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from src.skill_extractor import extract_skills as local_extract_skills, get_nlp
from src.gap_detector import detect_gaps, compute_skill_similarity


def get_config_val(key: str, default: str = "") -> str:
    """
    Safely retrieves configuration values, prioritizing Streamlit Secrets (for Cloud deployment)
    and falling back to environment variables / .env.
    """
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            val = str(st.secrets[key]).strip()
            if val:
                return val
    except Exception:
        pass
    return os.getenv(key, default).strip()

# ─── Domain Acronym & Normalization Map ──────────────────────────────────────
ACRONYM_NORMALIZATION_MAP = {
    "bms": "Battery Management System",
    "battery management systems": "Battery Management System",
    "can bus": "CAN Bus Diagnostics",
    "can bus diagnostics": "CAN Bus Diagnostics",
    "ci/cd": "CI/CD Pipelines",
    "cicd": "CI/CD Pipelines",
    "aws": "AWS Cloud",
    "amazon web services": "AWS Cloud",
    "ev safety": "Electric Vehicle Safety",
    "osha": "OSHA Safety Compliance",
    "mlt": "Medical Laboratory Technology",
    "pos": "POS Systems",
    "pos systems": "POS Systems",
    "bim": "Building Information Modeling (BIM)",
    "gd&t": "GD&T",
    "gdt": "GD&T",
    "rcc": "RCC Construction",
    "plc": "PLC Automation",
    "cnc": "CNC Programming",
}

SECTOR_SSC_MAP = {
    "Automotive": "Automotive Skills Development Council (ASDC)",
    "IT": "IT-ITeS Sector Skill Council (NASSCOM)",
    "Textile": "Textile Sector Skill Council (TSC)",
    "Healthcare": "Healthcare Sector Skill Council (HSSC)",
    "Construction": "Construction Skill Development Council (CSDCI)",
    "Retail/E-commerce": "Retailers Association's Skill Council of India (RASCI)",
    "General": "National Skill Development Corporation (NSDC)",
}


def normalize_skill_name(skill_name: str) -> str:
    """
    Normalizes domain abbreviations and variations without destroying unrelated terms.
    e.g., 'BMS' -> 'Battery Management System', 'CAN Bus' -> 'CAN Bus Diagnostics'.
    """
    cleaned = skill_name.strip()
    lower = cleaned.lower()
    return ACRONYM_NORMALIZATION_MAP.get(lower, cleaned)


def get_active_provider_config() -> Tuple[str, str, str]:
    """
    Returns (provider_type, model_name, api_key) according to .env configuration.
    """
    provider = get_config_val("AI_PROVIDER", "gemini").lower()
    gemini_key = get_config_val("GEMINI_API_KEY", "")
    gemini_model = get_config_val("GEMINI_MODEL", "gemini-2.5-flash")
    openrouter_key = get_config_val("OPENROUTER_API_KEY", "")
    openrouter_model = get_config_val("OPENROUTER_MODEL", "openrouter/free")

    if provider == "gemini" and gemini_key:
        return "gemini", gemini_model, gemini_key
    elif provider == "openrouter" and openrouter_key:
        return "openrouter", openrouter_model, openrouter_key
    elif gemini_key:
        return "gemini", gemini_model, gemini_key
    elif openrouter_key:
        return "openrouter", openrouter_model, openrouter_key
    else:
        return "local", "spaCy + RapidFuzz", ""


def get_provider_status_badge() -> Dict[str, str]:
    """
    Returns the transparent UI badge string and visual state for the active provider.
    """
    provider, model, key = get_active_provider_config()
    if provider == "gemini" and key:
        return {
            "status_text": f"🟢 Gemini 2.5 Flash — AI Enhanced ({model})",
            "provider": "Gemini 2.5 Flash",
            "tier": "gemini",
            "icon": "🟢",
        }
    elif provider == "openrouter" and key:
        return {
            "status_text": f"🟡 OpenRouter Free — Fallback ({model})",
            "provider": "OpenRouter Free",
            "tier": "openrouter",
            "icon": "🟡",
        }
    else:
        return {
            "status_text": "🔵 Local NLP — Offline Mode (spaCy + RapidFuzz)",
            "provider": "Local NLP",
            "tier": "local",
            "icon": "🔵",
        }


# ─── LLM Calling Functions with Safe Fallbacks ──────────────────────────────
def _call_gemini_api(prompt: str, model_name: str, api_key: str, response_json: bool = True) -> Optional[str]:
    """
    Calls Google Gemini API using the official google-genai SDK.
    Returns response text or None if error occurs.
    """
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        config_kwargs = {"temperature": 0.1}
        if response_json:
            config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**config_kwargs)
        response = client.models.generate_content(
            model=model_name or "gemini-2.5-flash",
            contents=prompt,
            config=config,
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        # Silent fallback without breaking caller
        return None
    return None


def _call_openrouter_api(prompt: str, model_name: str, api_key: str) -> Optional[str]:
    """
    Calls OpenRouter Free API using OpenAI-compatible HTTP endpoint.
    """
    try:
        import requests

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://skilltrack.ai",
            "X-Title": "SkillTrack AI Advisor",
        }
        payload = {
            "model": model_name or "openrouter/free",
            "messages": [
                {"role": "system", "content": "You are an expert vocational skill intelligence system. Respond with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=12)
        if r.status_code == 200:
            data = r.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception:
        return None
    return None


def _clean_and_parse_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Safely extracts and parses JSON even if wrapped in markdown code blocks.
    """
    if not raw_text:
        return None

    # Remove markdown code fence if present
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict) and "skills" in parsed:
            return parsed
        elif isinstance(parsed, list):
            return {"skills": parsed}
    except Exception:
        pass

    # Regex attempt to find the outermost JSON object
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    return None


# ─── Multi-Tier Skill Extraction Engine ──────────────────────────────────────
def extract_skills_with_ai(text: str, input_type: str = "Job Description") -> Tuple[List[Dict[str, Any]], str, str]:
    """
    Extracts structured technical skills from unstructured text.
    Fallback chain: Gemini -> OpenRouter -> Local spaCy/Regex NLP.

    Returns:
        (extracted_skills_list, provider_name, provider_badge_text)
    """
    provider_type, model_name, api_key = get_active_provider_config()

    prompt = f"""
You are an expert Industrial Skill Analyst and Curriculum Evaluator.
Analyze the following {input_type} text and extract all technical and operational competencies.

TEXT:
\"\"\"{text}\"\"\"

Return a valid JSON object matching this exact schema:
{{
  "skills": [
    {{
      "name": "Exact or canonical technical skill name (e.g., Battery Management System)",
      "category": "Industry sector e.g. Automotive, IT, Healthcare, Construction, Textile, or Retail",
      "type": "technical or operational",
      "importance": "high, medium, or low",
      "evidence": "Quoted snippet from the text justifying this skill"
    }}
  ]
}}

Rules:
- Extract specific, teachable vocational competencies (e.g. 'CAN Bus Diagnostics', 'Kubernetes', 'Battery Testing').
- Do not output general buzzwords like 'teamwork' or 'communication' unless specifically technical.
- Respond with JSON only. No explanations before or after.
"""

    raw_response = None
    provider_used = "Local NLP"
    status_badge = "🔵 Local NLP — Offline Mode"

    # 1. Try Gemini
    if provider_type == "gemini" and api_key:
        raw_response = _call_gemini_api(prompt, model_name, api_key, response_json=True)
        if raw_response:
            parsed = _clean_and_parse_json(raw_response)
            if not parsed:
                # Retry once with strict correction
                retry_prompt = prompt + "\n\nCRITICAL: Your previous response was not valid JSON. Output ONLY raw JSON."
                raw_response = _call_gemini_api(retry_prompt, model_name, api_key, response_json=True)
                parsed = _clean_and_parse_json(raw_response)

            if parsed and parsed.get("skills"):
                provider_used = "Gemini 2.5 Flash"
                status_badge = f"🟢 Gemini 2.5 Flash — AI Enhanced ({model_name})"
                return parsed.get("skills", []), provider_used, status_badge

    # 2. Try OpenRouter Fallback
    openrouter_key = get_config_val("OPENROUTER_API_KEY", "")
    openrouter_model = get_config_val("OPENROUTER_MODEL", "openrouter/free")
    if openrouter_key:
        raw_response = _call_openrouter_api(prompt, openrouter_model, openrouter_key)
        if raw_response:
            parsed = _clean_and_parse_json(raw_response)
            if parsed and parsed.get("skills"):
                provider_used = "OpenRouter Free"
                status_badge = f"🟡 OpenRouter Free — Fallback ({openrouter_model})"
                return parsed.get("skills", []), provider_used, status_badge

    # 3. Deterministic Local NLP Fallback (spaCy + Regex + Compound Noun Chunks)
    local_skills = list(local_extract_skills(text))
    extracted_names = set(s.lower() for s in local_skills)

    # Extract technical compound noun chunks from spaCy if available
    try:
        nlp = get_nlp()
        if nlp is not None:
            doc = nlp(text)
        stopwords = {
            "technician", "engineer", "specialist", "associate", "worker", "experience",
            "skills", "required", "years", "manager", "lead", "director", "expert",
            "developer", "architect", "pune", "mumbai", "nagpur", "nashik", "aurangabad",
            "kolhapur", "amravati", "certification", "text", "description",
        }
        for chunk in doc.noun_chunks:
            chunk_clean = chunk.text.strip()
            chunk_lower = chunk_clean.lower()
            words = set(chunk_lower.split())
            if not words.intersection(stopwords) and chunk_lower not in extracted_names:
                if len(chunk_clean.split()) >= 2:
                    local_skills.append(chunk_clean.title())
                    extracted_names.add(chunk_lower)
                elif any(t in chunk_lower for t in [
                    "docker", "kubernetes", "aws", "bms", "can", "pos", "rcc", "autocad",
                    "gdt", "bim", "cnc", "plc", "hematology", "biochemistry", "testing"
                ]):
                    local_skills.append(chunk_clean.title())
                    extracted_names.add(chunk_lower)
    except Exception:
        pass

    structured_local = []
    for s in local_skills:
        structured_local.append({
            "name": s,
            "category": "Technical",
            "type": "technical",
            "importance": "high",
            "evidence": s,
        })

    return structured_local, "Local NLP", "🔵 Local NLP — Offline Mode"


# ─── Grounded AI Executive Summary Generator ─────────────────────────────────
def generate_ai_executive_summary(
    input_text: str,
    input_type: str,
    skills_df: pd.DataFrame,
    critical_gaps: List[Dict[str, Any]],
    provider_name: str,
) -> str:
    """
    Generates a professional, concise executive summary explaining the alignment results.
    If an AI provider is active, uses the LLM grounded strictly in the calculated facts.
    If offline or on failure, uses an evidence-based deterministic template.
    """
    total_skills = len(skills_df)
    n_cov = len(skills_df[skills_df["gap_status"] == "covered"])
    n_par = len(skills_df[skills_df["gap_status"] == "partial"])
    n_mis = len(skills_df[skills_df["gap_status"] == "missing"])
    align_rate = round((n_cov / total_skills * 100), 1) if total_skills > 0 else 0.0

    missing_names = [g["skill"] for g in critical_gaps if g["status"] == "missing"]
    partial_names = [g["skill"] for g in critical_gaps if g["status"] == "partial"]

    skill_col = "Skill" if "Skill" in skills_df.columns else ("skill" if "skill" in skills_df.columns else None)
    if skill_col and not skills_df.empty and "gap_status" in skills_df.columns:
        cov_list = skills_df[skills_df["gap_status"] == "covered"][skill_col].tolist()
    else:
        cov_list = []

    # If Gemini or OpenRouter is available, request grounded synthesis
    if "Gemini" in provider_name or "OpenRouter" in provider_name:
        try:
            gemini_key = get_config_val("GEMINI_API_KEY", "")
            gemini_model = get_config_val("GEMINI_MODEL", "gemini-2.5-flash")

            facts_context = f"""
FACTS FROM SKILLTRACK ANALYTICAL ENGINE:
- Input Type: {input_type}
- Total Skills Detected: {total_skills}
- Fully Covered Skills ({n_cov}): {', '.join(cov_list) or 'None'}
- Partial Skills ({n_par}): {', '.join(partial_names) or 'None'}
- Missing Skills ({n_mis}): {', '.join(missing_names) or 'None'}
- Overall Curriculum Alignment: {align_rate}%
- Top Critical Gap: {missing_names[0] if missing_names else (partial_names[0] if partial_names else 'None')}
"""
            prompt = f"""
You are the AI Executive Advisor for SkillTrack AI.
Write a 3-paragraph executive summary analyzing these exact findings for a Vocational Director or ITI Principal.

{facts_context}

RULES:
- Base your explanation strictly on the facts above.
- Do NOT invent salary numbers, random employer counts, or fake certifications.
- Mention the alignment rate, the primary covered strengths, the critical gaps, and recommended faculty interventions.
- Professional, concise, enterprise-grade tone.
"""
            res = _call_gemini_api(prompt, gemini_model, gemini_key, response_json=False)
            if res and len(res.strip()) > 60:
                return res.strip()
        except Exception:
            pass

    # Deterministic Grounded Template Fallback
    top_gap = missing_names[0] if missing_names else (partial_names[0] if partial_names else "General alignment")
    summary = (
        f"The analyzed **{input_type.lower()}** exhibits a composite curriculum alignment rate of **{align_rate}%** "
        f"across **{total_skills} identified competencies**. "
        f"The vocational curriculum successfully covers **{n_cov} core skills**, while **{n_par} skills require module expansion** "
        f"and **{n_mis} competencies have zero current coverage**.\n\n"
        f"The most critical institutional priority identified is **{top_gap}**, where standard vocational syllabi currently "
        f"lack practical lab or simulation components. "
        f"To address this, targeted faculty upskilling workshops and supplementary curriculum modules should be prioritized "
        f"in partnership with relevant National Sector Skill Councils."
    )
    return summary


# ─── Main End-to-End Analysis Pipeline ───────────────────────────────────────
def analyze_requirement(
    text: str,
    input_type: str,
    curriculum_df: pd.DataFrame,
    demand_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    End-to-end analytical pipeline:
    1. AI / NLP Skill Extraction with provider fallback.
    2. Skill normalization & acronym resolution.
    3. Deterministic RapidFuzz curriculum similarity matching.
    4. Alignment tier classification (Covered, Partial, Missing).
    5. Critical skill gaps & faculty roadmap generation.
    6. Quick Wins opportunities.
    7. Grounded AI executive summary.
    """
    if not text or not text.strip():
        return {
            "error": "Input text is empty. Please enter or paste technical text to analyze.",
            "status_badge": get_provider_status_badge()["status_text"],
        }

    # Step 1: Extract candidate skills
    raw_skills, provider_used, status_badge = extract_skills_with_ai(text, input_type=input_type)

    if not raw_skills:
        return {
            "error": "No teachable technical skills were detected in the input. Try providing a more specific technical description.",
            "status_badge": status_badge,
        }

    # Step 2: Normalize skill names and deduplicate
    seen_skills = set()
    normalized_skills = []
    for item in raw_skills:
        orig_name = item.get("name", "").strip()
        if not orig_name:
            continue
        norm_name = normalize_skill_name(orig_name)
        if norm_name.lower() not in seen_skills:
            seen_skills.add(norm_name.lower())
            normalized_skills.append({
                "skill": norm_name,
                "original_name": orig_name,
                "category": item.get("category", "Technical"),
                "importance": item.get("importance", "high"),
                "evidence": item.get("evidence", orig_name),
            })

    # Step 3: Deterministic RapidFuzz matching against curriculum_df
    # We build a temporary demand DataFrame and run existing verified detect_gaps
    temp_demand_df = pd.DataFrame([
        {"skill": s["skill"], "demand_count": 1}
        for s in normalized_skills
    ])

    matched_gaps_df = detect_gaps(temp_demand_df, curriculum_df)

    # Merge metadata (category, importance, evidence) back into matched results
    meta_map = {s["skill"]: s for s in normalized_skills}
    matched_rows = []
    for _, r in matched_gaps_df.iterrows():
        sk = r["skill"]
        m_info = meta_map.get(sk, {})
        status = r["gap_status"]
        conf = float(r["match_confidence"])
        course = r["matched_course"]
        imp = m_info.get("importance", "medium")

        # Deterministic Priority
        if status == "missing":
            priority = "Critical" if imp == "high" else "High"
        elif status == "partial":
            priority = "High" if imp == "high" else "Medium"
        else:
            priority = "Low"

        matched_rows.append({
            "Skill": sk,
            "skill": sk,
            "Category": m_info.get("category", "Technical"),
            "Match Score": f"{conf:.1f}%",
            "raw_score": conf,
            "Status": status.capitalize(),
            "gap_status": status,
            "Best Matching Course": course,
            "Priority": priority,
            "Evidence": m_info.get("evidence", sk),
        })

    alignment_df = pd.DataFrame(matched_rows)

    # Step 4: Metric summary
    total_detected = len(alignment_df)
    n_cov = len(alignment_df[alignment_df["gap_status"] == "covered"])
    n_par = len(alignment_df[alignment_df["gap_status"] == "partial"])
    n_mis = len(alignment_df[alignment_df["gap_status"] == "missing"])
    align_pct = round((n_cov / total_detected * 100), 1) if total_detected > 0 else 0.0

    # Step 5: Critical Skill Gaps section
    critical_gaps = []
    for _, row in alignment_df[alignment_df["gap_status"].isin(["missing", "partial"])].iterrows():
        sk = row["Skill"]
        st = row["gap_status"]
        sc = row["raw_score"]
        mc = row["Best Matching Course"]
        cat = row["Category"]
        ssc = SECTOR_SSC_MAP.get(cat, "NSDC National Framework")

        if st == "missing":
            why = f"Demanded as a primary industry requirement, but standard vocational syllabi currently have zero direct coverage (match score {sc:.1f}%)."
            curriculum_state = "No sufficiently similar competency found in active vocational courses."
            action = f"Develop a new modular certificate course aligned with {ssc} benchmarks."
        else:
            why = f"Foundational concepts exist in '{mc}', but advanced practical competency is missing ({100-sc:.1f}% below industry readiness)."
            curriculum_state = f"Partially covered in '{mc}' at {sc:.1f}% match."
            action = f"Add a 1–2 day faculty workshop or dedicated laboratory exercise to '{mc}'."

        critical_gaps.append({
            "skill": sk,
            "status": st,
            "score": sc,
            "course": mc,
            "category": cat,
            "why_it_matters": why,
            "curriculum_coverage": curriculum_state,
            "recommended_action": action,
            "ssc": ssc,
        })

    # Step 6: Faculty Development Roadmap
    trainer_roadmap = []
    for gap in critical_gaps:
        prio = "HIGH PRIORITY" if gap["status"] == "missing" or gap["score"] < 65 else "MEDIUM"
        if gap["status"] == "missing":
            rec = f"Faculty Training of Trainers (ToT) in practical {gap['skill']}"
            reason = f"Essential to introduce new curriculum modules and hands-on laboratory exercises in {gap['category']}."
        else:
            rec = f"Advanced faculty upskilling & curriculum modernization workshop on {gap['skill']}"
            reason = f"Equips existing instructors of '{gap['course']}' to teach contemporary industry standards."

        trainer_roadmap.append({
            "priority": prio,
            "skill": gap["skill"],
            "training": rec,
            "reason": reason,
            "ssc": gap["ssc"],
        })

    # Step 7: Quick Wins
    quick_wins = []
    for _, row in alignment_df[alignment_df["gap_status"] == "partial"].iterrows():
        sk = row["Skill"]
        sc = row["raw_score"]
        mc = row["Best Matching Course"]
        gap_val = round(100 - sc, 1)
        effort = "Low (1–2 Day Workshop)" if gap_val < 25 else "Moderate (1-Week Module Update)"

        quick_wins.append({
            "skill": sk,
            "current_match": f"{sc:.1f}%",
            "course": mc,
            "intervention": f"Add specialized {sk} module to existing '{mc}' syllabus.",
            "impact": "Rapidly achieves industry job-market readiness for trainees.",
            "effort": effort,
        })

    # Step 8: Executive Summary
    exec_summary = generate_ai_executive_summary(
        text, input_type, alignment_df, critical_gaps, provider_used
    )

    return {
        "provider_name": provider_used,
        "status_badge": status_badge,
        "input_type": input_type,
        "input_text": text,
        "skills_detected": total_detected,
        "covered_count": n_cov,
        "partial_count": n_par,
        "missing_count": n_mis,
        "alignment_pct": align_pct,
        "alignment_df": alignment_df,
        "critical_gaps": critical_gaps,
        "trainer_roadmap": trainer_roadmap,
        "quick_wins": quick_wins,
        "executive_summary": exec_summary,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ─── Multi-Format Export Engines ─────────────────────────────────────────────
def export_analysis_to_excel(analysis: Dict[str, Any]) -> bytes:
    """
    Generates a professional multi-sheet Excel workbook containing:
    1. Executive Summary & KPIs
    2. Skill Alignment Matrix
    3. Critical Skill Gaps
    4. Faculty Development Roadmap & Quick Wins
    """
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Sheet 1: Executive Overview (always present and visible)
            overview_data = [
                {"Metric": "AI Intelligence Provider", "Value": analysis.get("provider_name", "SkillTrack AI")},
                {"Metric": "Input Classification", "Value": analysis.get("input_type", "General")},
                {"Metric": "Analysis Timestamp", "Value": analysis.get("timestamp", "")},
                {"Metric": "Total Skills Detected", "Value": analysis.get("skills_detected", 0)},
                {"Metric": "Covered Skills (≥80%)", "Value": analysis.get("covered_count", 0)},
                {"Metric": "Partial Gaps (50–80%)", "Value": analysis.get("partial_count", 0)},
                {"Metric": "Missing Gaps (<50%)", "Value": analysis.get("missing_count", 0)},
                {"Metric": "Overall Curriculum Alignment Rate", "Value": f"{analysis.get('alignment_pct', 0)}%"},
                {"Metric": "Executive Summary", "Value": analysis.get("executive_summary", "")},
            ]
            pd.DataFrame(overview_data).to_excel(writer, sheet_name="Executive Summary", index=False)

            # Sheet 2: Skill Alignment Table
            align_df = analysis.get("alignment_df")
            if isinstance(align_df, pd.DataFrame) and not align_df.empty:
                export_cols = ["Skill", "Category", "Match Score", "Status", "Best Matching Course", "Priority", "Evidence"]
                clean_align = align_df[[c for c in export_cols if c in align_df.columns]]
                clean_align.to_excel(writer, sheet_name="Skill Alignment Matrix", index=False)

            # Sheet 3: Critical Gaps
            gaps = analysis.get("critical_gaps", [])
            if gaps:
                gaps_records = [
                    {
                        "Skill": g["skill"],
                        "Status": g["status"].capitalize(),
                        "Match Confidence": f"{g['score']:.1f}%",
                        "Best Matching Course": g["course"],
                        "Why It Matters": g["why_it_matters"],
                        "Recommended Action": g["recommended_action"],
                        "Sector Skill Council": g["ssc"],
                    }
                    for g in gaps
                ]
                pd.DataFrame(gaps_records).to_excel(writer, sheet_name="Critical Skill Gaps", index=False)

            # Sheet 4: Faculty Roadmap & Quick Wins
            roadmap = analysis.get("trainer_roadmap", [])
            if roadmap:
                roadmap_df = pd.DataFrame(roadmap)
                roadmap_df.columns = ["Priority", "Competency", "Recommended Training", "Curriculum Justification", "Sector Skill Council"]
                roadmap_df.to_excel(writer, sheet_name="Faculty Roadmap", index=False)

            q_wins = analysis.get("quick_wins", [])
            if q_wins:
                q_df = pd.DataFrame(q_wins)
                q_df.columns = ["Skill", "Current Match", "Target Course", "Intervention Plan", "Expected Impact", "Estimated Effort"]
                q_df.to_excel(writer, sheet_name="Quick Wins", index=False)

        output.seek(0)
        return output.getvalue()
    except Exception:
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Executive Summary"
            ws.append(["Metric", "Value"])
            ws.append(["AI Intelligence Provider", analysis.get("provider_name", "SkillTrack AI")])
            ws.append(["Alignment Rate", f"{analysis.get('alignment_pct', 0)}%"])
            fb = io.BytesIO()
            wb.save(fb)
            fb.seek(0)
            return fb.getvalue()
        except Exception:
            return b""


def export_analysis_to_csv(analysis: Dict[str, Any]) -> bytes:
    """
    Returns CSV representation of the skill alignment table.
    """
    align_df = analysis.get("alignment_df")
    if isinstance(align_df, pd.DataFrame) and not align_df.empty:
        export_cols = ["Skill", "Category", "Match Score", "Status", "Best Matching Course", "Priority"]
        clean_df = align_df[[c for c in export_cols if c in align_df.columns]]
        return clean_df.to_csv(index=False).encode("utf-8")
    return b""
