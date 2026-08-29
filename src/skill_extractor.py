import re
from typing import List, Optional, Set
import spacy
from spacy.tokens import Doc

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
]

# Global cache for spaCy NLP model
_NLP = None


def get_nlp():
    """
    Lazy loader for spaCy English pipeline.
    """
    global _NLP
    if _NLP is None:
        try:
            _NLP = spacy.load("en_core_web_sm")
        except OSError:
            spacy.cli.download("en_core_web_sm")
            _NLP = spacy.load("en_core_web_sm")
    return _NLP


def normalize_string(s: str) -> str:
    """
    Normalize text for robust matching by lowercasing and standardizing whitespace.
    """
    return re.sub(r"[^\w\s\+]", " ", s).strip().lower()


def extract_skills(text: Optional[str]) -> List[str]:
    """
    Extract technical and vocational skills from input text using spaCy and keyword matching.

    Steps:
    1. Validate input; returns empty list if None, non-string, or very short.
    2. Extract noun chunks and named entities as candidate phrases.
    3. Match candidate phrases and normalized text against canonical SKILL_KEYWORDS.
    4. Return a clean, deduplicated list of matched skills.
    """
    if not text or not isinstance(text, str):
        return []

    cleaned_text = text.strip()
    if len(cleaned_text) < 3:
        return []

    nlp = get_nlp()
    doc: Doc = nlp(cleaned_text)

    # 1. Extract candidate strings from spaCy noun chunks, named entities, and tokens
    candidates: Set[str] = set()

    for chunk in doc.noun_chunks:
        cand = chunk.text.strip()
        if cand:
            candidates.add(cand)

    for ent in doc.ents:
        cand = ent.text.strip()
        if cand:
            candidates.add(cand)

    for token in doc:
        if not token.is_stop and not token.is_punct and len(token.text) > 1:
            candidates.add(token.text.strip())

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
