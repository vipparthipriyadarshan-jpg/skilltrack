import os
import socket
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
import requests
from dotenv import load_dotenv

# Force IPv4 socket resolution on Windows to avoid WinError 10065 (unreachable host on IPv6)
try:
    import urllib3.util.connection as urllib3_cn
    urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
except Exception:
    pass

# Load environment variables from .env if present
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SECTOR_SEARCH_CONFIG = {
    "IT": {
        "primary": "Software Developer Python",
        "fallbacks": ["Python Developer", "Cloud Engineer", "React Developer", "DevOps Engineer", "Software Engineer"],
        "context": "Key competencies: Python, Docker, Kubernetes, Cloud Computing, SQL, REST API, CI/CD, Git.",
    },
    "Automotive": {
        "primary": "Automotive Engineer Vehicle",
        "fallbacks": ["Mechanical Engineer", "Automobile Engineer", "Automotive Maintenance", "CAD Engineer"],
        "context": "Key competencies: Automotive Diagnostics, Electric Vehicle Systems, CAN Bus Diagnostics, SolidWorks, AutoCAD, Preventive Maintenance.",
    },
    "Textile": {
        "primary": "Textile Garment Quality",
        "fallbacks": ["Textile Production", "Apparel Designer", "Weaving Loom", "Garment Manufacturing"],
        "context": "Key competencies: Textile Quality Control, Digital Textile Printing, Loom Operation, Pattern Design, Color Fastness Testing, Garment Manufacturing.",
    },
    "Healthcare": {
        "primary": "Staff Nurse Patient Care",
        "fallbacks": ["Medical Laboratory Technician", "Hospital Nurse", "Healthcare Assistant", "Clinical Specialist"],
        "context": "Key competencies: Patient Care, Vital Signs Monitoring, Basic Life Support, IV Cannulation, Clinical Documentation, Wound Dressing.",
    },
    "Construction": {
        "primary": "Civil Site Engineer",
        "fallbacks": ["Construction Engineer", "Site Supervisor Civil", "Building Construction", "AutoCAD Engineer"],
        "context": "Key competencies: AutoCAD, Site Supervision, RCC Construction, Safety Compliance, Quantity Surveying, BOQ Preparation.",
    },
    "Retail/E-commerce": {
        "primary": "Store Manager Retail",
        "fallbacks": ["Retail Sales Executive", "Ecommerce Operations", "Inventory Specialist", "Merchandiser"],
        "context": "Key competencies: Inventory Management, POS Billing, Customer Service, Visual Merchandising, Supply Chain Operations.",
    },
}


def fetch_live_jobs_adzuna(
    sector: str = "IT",
    district: str = "Pune",
    count: int = 6,
    country: str = "in",
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Fetch live job postings from Adzuna API (Free Tier) with IPv4 resolution
    and automatic query fallbacks across all 6 sectors and 7 Maharashtra districts.

    Returns:
        (DataFrame of new jobs, None) if successful.
        (None, error_message) if API fails or credentials are not configured.
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        return (
            None,
            "Adzuna API credentials not configured. Please set 'ADZUNA_APP_ID' and "
            "'ADZUNA_APP_KEY' in your .env file to connect to live Adzuna feeds.",
        )

    config = SECTOR_SEARCH_CONFIG.get(sector, SECTOR_SEARCH_CONFIG["IT"])
    queries_to_try = [config["primary"]] + config["fallbacks"]
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    target_count = min(max(count, 1), 20)

    results = []
    last_error = None

    # Multi-strategy search:
    # Strategy 1: Try with district filter
    # Strategy 2: If district has sparse results, query national pool and tag with selected district
    for with_where in [True, False]:
        if len(results) >= target_count:
            break

        for query in queries_to_try:
            if len(results) >= target_count:
                break

            params = {
                "app_id":           app_id,
                "app_key":          app_key,
                "results_per_page": target_count,
                "what":             query,
                "content-type":     "application/json",
            }
            if with_where and district:
                params["where"] = district

            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code in (401, 403):
                    return None, f"Adzuna API authentication failed (HTTP {response.status_code}). Please verify your ADZUNA_APP_ID and ADZUNA_APP_KEY."

                if response.status_code == 200:
                    data = response.json()
                    new_items = data.get("results", [])
                    # Deduplicate by item ID
                    existing_ids = {r.get("id") for r in results}
                    for it in new_items:
                        if it.get("id") not in existing_ids:
                            results.append(it)
                            existing_ids.add(it.get("id"))
                            if len(results) >= target_count:
                                break
                else:
                    last_error = f"Adzuna HTTP {response.status_code}"
            except requests.exceptions.RequestException as e:
                last_error = f"Network connection error: {e}"
                break

    # If API yielded results, format them into pipeline-ready DataFrame
    if results:
        jobs_list = []
        for i, item in enumerate(results[:target_count], 1):
            raw_id = item.get("id", i)
            job_id = f"LIVE_{sector[:2].upper()}_{raw_id}"
            title  = item.get("title", f"Live {sector} Professional")
            # Strip HTML tags if any in title
            title  = title.replace("<strong>", "").replace("</strong>", "").strip()

            desc_raw = item.get("description", "")
            desc_raw = desc_raw.replace("<strong>", "").replace("</strong>", "").strip()

            company = item.get("company", {}).get("display_name", "Industry Employer")
            loc_info = item.get("location", {}).get("display_name", district)

            # Construct rich description ensuring spaCy NLP extracts real domain skills
            combined_desc = (
                f"{title} at {company} ({loc_info}). "
                f"{desc_raw} "
                f"{config['context']}"
            )

            jobs_list.append({
                "job_id":          job_id,
                "job_title":       title,
                "sector":          sector,
                "district":        district,
                "job_description": combined_desc,
            })

        new_jobs_df = pd.DataFrame(jobs_list)
        return new_jobs_df, None

    # If live API had no results or failed, return helpful message
    err_detail = f" ({last_error})" if last_error else ""
    return None, f"Adzuna returned 0 postings for {sector} in {district}{err_detail}. Use the demo live batch button to test immediately."


def generate_demo_live_jobs(
    sector: str = "IT",
    district: str = "Pune",
    count: int = 5,
) -> pd.DataFrame:
    """
    Generates a realistic live simulated batch of job postings across all 6 sectors
    and 7 Maharashtra districts for demonstration, evaluation, or offline testing.
    """
    templates = {
        "IT": [
            ("Cloud Platform Engineer", "Seeking Cloud Platform Engineer with Kubernetes, Docker, Terraform, and AWS Cloud architecture experience in Maharashtra."),
            ("Senior Python NLP Specialist", "Hiring NLP Specialist with Python, LangChain, PyTorch, Vector Databases, and REST API development skills."),
            ("Cyber Incident Responder", "Urgent requirement for Cyber Responder skilled in SIEM, Threat Hunting, Penetration Testing, and Vulnerability Assessment."),
            ("Full Stack React/Node Developer", "Looking for Full Stack Developer proficient in React, Tailwind CSS, PostgreSQL, and Git version control."),
            ("Database Performance Architect", "Hiring DBA with deep expertise in PostgreSQL, MySQL, Database Optimization, and SQL Query Tuning."),
        ],
        "Automotive": [
            ("Battery Management Systems Lead", "Hiring Lead BMS Engineer skilled in Electric Vehicle Battery Management, Battery Chemistry, and MATLAB Simulink in Maharashtra."),
            ("ADAS Calibration Field Engineer", "Looking for ADAS Engineer experienced in ADAS Sensor Calibration, Radar Diagnostics, LiDAR, and Telematics."),
            ("Automotive Quality Assurance Lead", "Seeking QA Engineer skilled in Six Sigma, Total Quality Management, CMM Inspection, and GD&T."),
            ("CNC Machine Center Programmer", "Hiring CNC Programmer proficient in CNC Programming, Lathe Operation, G-Code, and Blueprint Reading."),
            ("EV Diagnostics Specialist", "Opening for Automotive Diagnostics Specialist with CAN Bus Diagnostics, Brake System Repair, and Vehicle Maintenance."),
        ],
        "Textile": [
            ("Digital Sublimation Print Master", "Looking for Specialist in Digital Textile Printing, Sublimation Printing, Color Fastness Testing, and RIP Software in Maharashtra."),
            ("Sustainable Dyeing Technical Lead", "Hiring Technical Lead experienced in Sustainable Dyeing, Chemical Processing, Effluent Treatment, and Yarn Dyeing."),
            ("Apparel Pattern CAD Designer", "Seeking Pattern Designer skilled in Gerber CAD, Pattern Grading, Garment Fitting, and Sewing Techniques."),
            ("Loom Operations Supervisor", "Opening for Loom Supervisor with Loom Operation, Yarn Quality Control, Spinning, and Production Planning skills."),
            ("Weaving Preventive Maintenance Tech", "Hiring Maintenance Tech skilled in Airjet Loom Maintenance, Mechanical Repair, and Electrical Troubleshooting."),
        ],
        "Healthcare": [
            ("ICU Critical Care Specialist Nurse", "Urgent requirement for ICU Nurse skilled in Basic Life Support, Patient Care, Vital Signs Monitoring, and Clinical Documentation in Maharashtra."),
            ("Medical Laboratory Technologist", "Hiring Lab Technologist experienced in Pathology Sample Processing, Hematology Diagnostics, Clinical Chemistry, and Lab Safety Protocols."),
            ("Dialysis Center Operations Lead", "Looking for Dialysis Tech proficient in Hemodialysis Equipment Operation, Patient Cannulation, and Renal Care Monitoring."),
            ("Emergency Medical Responder", "Opening for Emergency Medical Tech skilled in Trauma Triage, Advanced Cardiac Life Support, and Emergency Response Care."),
            ("Hospital Infection Control Officer", "Seeking Healthcare Specialist skilled in Biomedical Waste Management, Infection Control Protocols, and Hospital Accreditation Standards."),
        ],
        "Construction": [
            ("Senior Civil Site Project Engineer", "Hiring Civil Engineer proficient in AutoCAD Site Planning, RCC Construction, Quantity Surveying, and BOQ Preparation in Maharashtra."),
            ("Structural Design & BIM Engineer", "Looking for Structural Engineer skilled in Structural Detailing, Revit BIM, Concrete Mix Design, and Foundation Engineering."),
            ("Construction Safety Compliance Officer", "Urgent requirement for Safety Officer skilled in Site Safety Compliance, Hazard Identification, OSHA Standards, and Scaffold Inspection."),
            ("Highway & Earthwork Survey Specialist", "Opening for Surveyor proficient in Total Station Survey, GIS Mapping, Road Earthwork Estimation, and Leveling."),
            ("Quality Control Concrete Technologist", "Hiring QC Civil Engineer skilled in Compressive Strength Testing, Slump Test, Non-Destructive Testing, and IS Code Compliance."),
        ],
        "Retail/E-commerce": [
            ("Omnichannel Store Operations Manager", "Hiring Store Manager skilled in Inventory Management, POS Billing Systems, Retail Store Operations, and Visual Merchandising in Maharashtra."),
            ("E-Commerce Catalog & Listing Specialist", "Looking for E-commerce Specialist experienced in Product Catalog Management, SEO Keyword Optimization, Order Fulfillment, and Marketplace Portals."),
            ("Retail Inventory & Supply Chain Planner", "Opening for Retail Planner skilled in Demand Forecasting, Stock Replenishment, Barcode Inventory Tracking, and Shrinkage Control."),
            ("Customer Experience & CRM Lead", "Seeking CRM Manager skilled in Customer Relationship Management, Customer Retention Strategies, Loyalty Programs, and Omnichannel Support."),
            ("Visual Merchandising & Retail Stylist", "Urgent requirement for Visual Merchandiser skilled in Store Layout Optimization, Planogram Compliance, Window Display Styling, and Promotional POS Signage."),
        ],
    }

    raw_items = templates.get(sector, templates["IT"])[:count]
    rows = []
    for i, (title, desc) in enumerate(raw_items, 1):
        rows.append(
            {
                "job_id": f"LIVE_SIM_{sector[:2].upper()}_{i}_{district[:3].upper()}",
                "job_title": title,
                "sector": sector,
                "district": district,
                "job_description": desc,
            }
        )
    return pd.DataFrame(rows)
