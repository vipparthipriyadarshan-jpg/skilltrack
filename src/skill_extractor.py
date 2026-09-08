import re
from typing import List, Optional, Set
import pandas as pd
try:
    import spacy
    from spacy.tokens import Doc
    SPACY_AVAILABLE = True
except (ImportError, KeyError, Exception):
    spacy = None
    Doc = None
    SPACY_AVAILABLE = False

# Expanded, curated catalog of 70+ technical and vocational skills across IT, Automotive, and Textile
SKILL_KEYWORDS = [
    # --- Information Technology / Software / Data / Cloud ---
    "Python",
    "React",
    "PostgreSQL",
    "MySQL",
    "Docker",
    "Kubernetes",
    "REST API",
    "Git",
    "CI/CD",
    "SQL",
    "SQL Query Tuning",
    "Power BI",
    "Pandas",
    "Excel",
    "Data Modeling",
    "Statistical Analysis",
    "Tableau",
    "AWS Cloud",
    "Cloud Computing",
    "Terraform",
    "Linux",
    "Linux System Administration",
    "Jenkins",
    "PyTorch",
    "LangChain",
    "Natural Language Processing",
    "Scikit-Learn",
    "Vector Databases",
    "Machine Learning",
    "HTML5",
    "CSS3",
    "JavaScript",
    "Tailwind CSS",
    "Redux",
    "Frontend Development",
    "Database Optimization",
    "Backup Recovery",
    "Network Security",
    "Threat Hunting",
    "SIEM",
    "Penetration Testing",
    "Vulnerability Assessment",
    "Cybersecurity",
    "Networking",
    "Technical Troubleshooting",
    "Bash Scripting",
    "DevOps",
    # --- Automotive & Mechanical Engineering ---
    "Electric Vehicle Battery Management",
    "Battery Chemistry",
    "MATLAB Simulink",
    "CAN Bus Diagnostics",
    "Six Sigma",
    "Total Quality Management",
    "CMM Inspection",
    "Quality Assurance",
    "GD&T",
    "CNC Programming",
    "Lathe Operation",
    "G-Code",
    "Milling",
    "Blueprint Reading",
    "AutoCAD",
    "SolidWorks",
    "CATIA 3D Modeling",
    "Sheet Metal Design",
    "Prototyping",
    "Engine Overhaul",
    "Brake System Repair",
    "Wheel Alignment",
    "Automotive Diagnostics",
    "Vehicle Maintenance",
    "ADAS Sensor Calibration",
    "Radar Diagnostics",
    "LiDAR",
    "Automotive Telematics",
    # --- Textile & Apparel Manufacturing ---
    "Loom Operation",
    "Airjet Loom Maintenance",
    "Yarn Quality Control",
    "Spinning",
    "Weaving",
    "Production Planning",
    "Digital Textile Printing",
    "Sublimation Printing",
    "Color Fastness Testing",
    "Fabric Inspection",
    "RIP Software",
    "Stitching Quality Control",
    "Apparel Testing",
    "Defect Analysis",
    "Sustainable Dyeing",
    "Chemical Processing",
    "Effluent Treatment",
    "Yarn Dyeing",
    "Shade Matching",
    "Pattern Grading",
    "Gerber CAD",
    "Garment Fitting",
    "Sewing Techniques",
    "Sample Making",
    "Mechanical Repair",
    "Preventive Maintenance",
    "Electrical Troubleshooting",
    # --- Healthcare & Medical ---
    "Patient Care",
    "Vital Signs Monitoring",
    "Wound Dressing",
    "IV Cannulation",
    "Basic Life Support",
    "Advanced Cardiac Life Support",
    "Patient Triage",
    "Emergency Trauma Care",
    "Clinical Biochemistry",
    "Hematology Testing",
    "Blood Sample Collection",
    "Microscopy",
    "Lab Quality Control",
    "Pathology Lab Quality Control",
    "Vaccination Administration",
    "Maternal Child Health",
    "Disease Surveillance",
    "Community Health Education",
    "Drug Dispensing",
    "Pharmaceutical Inventory Management",
    "Prescription Verification",
    "Dosage Calculation",
    "X-Ray Machine Operation",
    "CT Scan Assistance",
    "MRI Patient Positioning",
    "Radiation Safety",
    "PACS System",
    # --- Construction & Civil Engineering ---
    "AutoCAD",
    "Structural Drawings",
    "Quantity Takeoff",
    "BOQ Preparation",
    "Construction Cost Estimation",
    "MS Project Scheduling",
    "Contract Management",
    "Building Safety Compliance",
    "RCC Design",
    "Steel Structure Design",
    "STAAD Pro",
    "Load Calculation",
    "Structural Drawing Reading",
    "Plumbing Installation",
    "Electrical Installation",
    "Fire Safety Audit",
    "Concrete Mix Design",
    "Brick Masonry",
    "Plastering",
    "Formwork Erection",
    "RCC Slab Casting",
    "Total Station Survey",
    "Levelling",
    "GPS Survey",
    "Material Procurement",
    "HVAC System Design",
    # --- Retail & E-commerce ---
    "Marketplace Listing Management",
    "Inventory Management",
    "Demand Forecasting",
    "Logistics Coordination",
    "Retail Customer Service",
    "Visual Merchandising",
    "POS System Operation",
    "SEO Optimization",
    "Google Ads Management",
    "Social Media Marketing",
    "Email Marketing",
    "Analytics Reporting",
    "Vendor Management",
    "Procurement Planning",
    "CRM Software",
    "Customer Service",
    "Complaint Resolution",
    "Warehouse Management System",
    "Category Management",
    "Pricing Strategy",
]


# Global cache for spaCy NLP model
_NLP = None


def get_nlp():
    """
    Lazy loader for spaCy English pipeline with safe error resilience.
    Uses pre-installed 'en_core_web_sm' from requirements.txt without runtime downloads.
    """
    global _NLP, SPACY_AVAILABLE, spacy
    if not SPACY_AVAILABLE or spacy is None:
        return None
    if _NLP is None:
        try:
            _NLP = spacy.load("en_core_web_sm")
        except Exception:
            _NLP = None
            SPACY_AVAILABLE = False
    return _NLP


def normalize_string(s: str) -> str:
    """
    Normalize text for robust matching by lowercasing and standardizing whitespace.
    """
    return re.sub(r"[^\w\s\+]", " ", s).strip().lower()


def extract_skills(text: Optional[str]) -> List[str]:
    """
    Extract technical and vocational skills from input text using spaCy and keyword matching.

    Handles empty, None, NaN, numeric, or malformed text gracefully without crashing.
    """
    if text is None:
        return []

    # Handle float / NaN / non-string gracefully
    if not isinstance(text, str):
        if pd.isna(text):
            return []
        text = str(text)

    cleaned_text = text.strip()
    if not cleaned_text or len(cleaned_text) < 3:
        return []

    candidates: Set[str] = set()
    nlp = get_nlp()
    if nlp is not None:
        try:
            doc = nlp(cleaned_text)
            for chunk in getattr(doc, "noun_chunks", []):
                cand = chunk.text.strip()
                if cand:
                    candidates.add(cand)

            for ent in getattr(doc, "ents", []):
                cand = ent.text.strip()
                if cand:
                    candidates.add(cand)

            for token in doc:
                if not token.is_stop and not token.is_punct and len(token.text) > 1:
                    candidates.add(token.text.strip())
        except Exception:
            pass

    # Build normalized representations
    norm_candidates = [re.sub(r"\s+", " ", normalize_string(c)) for c in candidates if c]
    norm_full_text = re.sub(r"\s+", " ", normalize_string(cleaned_text))

    matched_skills: List[str] = []

    # Sort keywords by length descending so longer compound phrases take priority
    sorted_keywords = sorted(SKILL_KEYWORDS, key=lambda k: len(k), reverse=True)

    for skill in sorted_keywords:
        norm_skill = re.sub(r"\s+", " ", normalize_string(skill))
        if not norm_skill:
            continue

        is_matched = False

        # Pattern with word boundaries for the normalized skill
        pattern = r"(?<!\w)" + re.escape(norm_skill) + r"(?!\w)"

        # Check in noun chunks / candidate phrases
        for nc in norm_candidates:
            if re.search(pattern, nc):
                is_matched = True
                break

        # Check in full text as fallback
        if not is_matched and re.search(pattern, norm_full_text):
            is_matched = True

        if is_matched and skill not in matched_skills:
            matched_skills.append(skill)

    # Maintain original catalog order for consistency
    ordered_matched = [s for s in SKILL_KEYWORDS if s in matched_skills]
    return ordered_matched


def main():
    test_cases = [
        "",
        " ",
        "a",
        "Looking for a Full Stack Developer proficient in Python, React, PostgreSQL, Docker, and REST API development. Experience with Git and CI/CD pipelines is required.",
        "Seeking Data Analyst skilled in Python, SQL, Power BI, Pandas, and Excel data modeling. Strong statistical analysis and Tableau experience preferred.",
        "Seeking DBA with deep knowledge of PostgreSQL, MySQL, Database Optimization, Backup Recovery, and SQL Query Tuning.",
        "Cloud Support Specialist needed with AWS Cloud, Linux, Bash Scripting, Networking, and Technical Troubleshooting skills.",
        "Mechanical Design Engineer needed with expertise in AutoCAD, SolidWorks, CATIA 3D Modeling, Sheet Metal Design, and Prototyping.",
        "Maintenance Technician required for Airjet Loom Maintenance, Mechanical Repair, Preventive Maintenance, and Electrical Troubleshooting.",
    ]

    print("=== Testing Updated Skill Extractor ===")
    for idx, case in enumerate(test_cases, 1):
        extracted = extract_skills(case)
        print(f"\nTest {idx}: {case!r}")
        print(f"Extracted ({len(extracted)} skills): {extracted}")


if __name__ == "__main__":
    main()
