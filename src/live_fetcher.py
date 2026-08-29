import os
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
import requests
from dotenv import load_dotenv

# Load environment variables from .env if present
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SECTOR_QUERY_MAP = {
    "IT": "Software Developer Python React",
    "Automotive": "Automotive Engineer Vehicle Mechanical",
    "Textile": "Textile Production Quality Garment",
}


def fetch_live_jobs_adzuna(
    sector: str = "IT",
    district: str = "Pune",
    count: int = 8,
    country: str = "in",
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Fetch live job postings from Adzuna API (Free Tier).

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
            "'ADZUNA_APP_KEY' in your .env file or environment variables to connect to live Adzuna feeds.",
        )

    search_query = SECTOR_QUERY_MAP.get(sector, f"{sector} Engineer")
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": min(max(count, 1), 20),
        "what": search_query,
        "where": district,
        "content-type": "application/json",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code in (401, 403):
            return None, f"Adzuna API authentication failed (HTTP {response.status_code}). Please verify your ADZUNA_APP_ID and ADZUNA_APP_KEY."

        if response.status_code != 200:
            return None, f"Adzuna API returned HTTP {response.status_code}: {response.text[:180]}"

        data = response.json()
        results = data.get("results", [])

        if not results:
            return None, f"No live postings found for sector '{sector}' in '{district}' on Adzuna API."

        jobs_list = []
        for i, item in enumerate(results, 1):
            job_id = f"LIVE_{sector[:2].upper()}_{item.get('id', i)}"
            title = item.get("title", f"Live {sector} Professional")
            desc = item.get("description", f"Hiring for {title} with skills in {search_query}")

            jobs_list.append(
                {
                    "job_id": job_id,
                    "job_title": title,
                    "sector": sector,
                    "district": district,
                    "job_description": desc,
                }
            )

        new_jobs_df = pd.DataFrame(jobs_list)
        return new_jobs_df, None

    except requests.exceptions.RequestException as e:
        return None, f"Network error while connecting to Adzuna API: {e}"
    except Exception as e:
        return None, f"Unexpected error during live job ingestion: {e}"


def generate_demo_live_jobs(
    sector: str = "IT",
    district: str = "Pune",
    count: int = 5,
) -> pd.DataFrame:
    """
    Generates a realistic live simulated batch of job postings for evaluation
    and demonstration when Adzuna API credentials are not yet configured.
    """
    templates = {
        "IT": [
            ("Cloud Platform Engineer", "Seeking Cloud Platform Engineer with Kubernetes, Docker, Terraform, and AWS Cloud architecture experience in Pune."),
            ("Senior Python NLP Specialist", "Hiring NLP Specialist with Python, LangChain, PyTorch, Vector Databases, and REST API development skills."),
            ("Cyber Incident Responder", "Urgent requirement for Cyber Responder skilled in SIEM, Threat Hunting, Penetration Testing, and Vulnerability Assessment."),
            ("Full Stack React/Node Developer", "Looking for Full Stack Developer proficient in React, Tailwind CSS, PostgreSQL, and Git version control."),
            ("Database Performance Architect", "Hiring DBA with deep expertise in PostgreSQL, MySQL, Database Optimization, and SQL Query Tuning."),
        ],
        "Automotive": [
            ("Battery Management Systems Lead", "Hiring Lead BMS Engineer skilled in Electric Vehicle Battery Management, Battery Chemistry, and MATLAB Simulink."),
            ("ADAS Calibration Field Engineer", "Looking for ADAS Engineer experienced in ADAS Sensor Calibration, Radar Diagnostics, LiDAR, and Telematics."),
            ("Automotive Quality Assurance Lead", "Seeking QA Engineer skilled in Six Sigma, Total Quality Management, CMM Inspection, and GD&T."),
            ("CNC Machine Center Programmer", "Hiring CNC Programmer proficient in CNC Programming, Lathe Operation, G-Code, and Blueprint Reading."),
            ("EV Diagnostics Specialist", "Opening for Automotive Diagnostics Specialist with CAN Bus Diagnostics, Brake System Repair, and Vehicle Maintenance."),
        ],
        "Textile": [
            ("Digital Sublimation Print Master", "Looking for Specialist in Digital Textile Printing, Sublimation Printing, Color Fastness Testing, and RIP Software."),
            ("Sustainable Dyeing Technical Lead", "Hiring Technical Lead experienced in Sustainable Dyeing, Chemical Processing, Effluent Treatment, and Yarn Dyeing."),
            ("Apparel Pattern CAD Designer", "Seeking Pattern Designer skilled in Gerber CAD, Pattern Grading, Garment Fitting, and Sewing Techniques."),
            ("Loom Operations Supervisor", "Opening for Loom Supervisor with Loom Operation, Yarn Quality Control, Spinning, and Production Planning skills."),
            ("Weaving Preventive Maintenance Tech", "Hiring Maintenance Tech skilled in Airjet Loom Maintenance, Mechanical Repair, and Electrical Troubleshooting."),
        ],
    }

    raw_items = templates.get(sector, templates["IT"])[:count]
    rows = []
    for i, (title, desc) in enumerate(raw_items, 1):
        rows.append(
            {
                "job_id": f"LIVE_DEMO_{sector[:2].upper()}_{i}",
                "job_title": title,
                "sector": sector,
                "district": district,
                "job_description": desc,
            }
        )
    return pd.DataFrame(rows)
