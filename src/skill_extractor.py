import re
from typing import List, Optional, Set
import spacy
from spacy.tokens import Doc

# Comprehensive catalog of 60+ real technical and vocational skills across IT, Automotive, and Textile
SKILL_KEYWORDS = [
    # --- Information Technology ---
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
    "Power BI",
    "Pandas",
    "Excel",
    "Tableau",
    "AWS Cloud",
    "Terraform",
    "Linux",
    "Jenkins",
    "PyTorch",
    "LangChain",
    "Natural Language Processing",
    "Scikit-Learn",
    "Vector Databases",
    "HTML5",
    "CSS3",
    "JavaScript",
    "Tailwind CSS",
    "Redux",
    "Database Optimization",
    "Network Security",
    "Threat Hunting",
    "SIEM",
    "Penetration Testing",
    "Vulnerability Assessment",
    "Bash Scripting",
    # --- Automotive ---
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
    "Engine Overhaul",
    "Brake System Repair",
    "Wheel Alignment",
    "Automotive Diagnostics",
    "Vehicle Maintenance",
    "ADAS Sensor Calibration",
    "Radar Diagnostics",
    "LiDAR",
    "Automotive Telematics",
    # --- Textile ---
    "Loom Operation",
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
            # Fallback if model not installed yet
            spacy.cli.download("en_core_web_sm")
            _NLP = spacy.load("en_core_web_sm")
    return _NLP


def normalize_string(s: str) -> str:
    """
    Normalize text for robust matching by lowercasing and removing punctuation.
    """
    return re.sub(r"[^\w\s\+]", "", s).strip().lower()


def extract_skills(text: Optional[str]) -> List[str]:
    """
    Extract technical and vocational skills from input text using spaCy.

    Steps:
    1. Validate input; returns empty list if None, non-string, or very short.
    2. Extract noun chunks and named entities as candidate phrases.
    3. Match candidate phrases and direct occurrences against canonical SKILL_KEYWORDS.
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
        candidates.add(chunk.text.strip())

    for ent in doc.ents:
        candidates.add(ent.text.strip())

    for token in doc:
        if not token.is_stop and not token.is_punct and len(token.text) > 1:
            candidates.add(token.text.strip())

    # Build normalized candidates dictionary
    norm_candidates = {normalize_string(cand): cand for cand in candidates if cand}
    norm_full_text = normalize_string(cleaned_text)

    matched_skills: List[str] = []

    # 2. Filter against canonical SKILL_KEYWORDS
    for skill in SKILL_KEYWORDS:
        norm_skill = normalize_string(skill)
        if not norm_skill:
            continue

        # Check candidate match
        is_matched = False
        if norm_skill in norm_candidates:
            is_matched = True
        else:
            # Check if normalized skill appears as a candidate substring or in candidate phrases
            for nc in norm_candidates:
                # Word boundary match inside candidate or exact match
                pattern = r"\b" + re.escape(norm_skill) + r"\b"
                if re.search(pattern, nc):
                    is_matched = True
                    break

            # Fallback: check whole text boundary match if spaCy chunking split it
            if not is_matched:
                pattern = r"\b" + re.escape(norm_skill) + r"\b"
                if re.search(pattern, norm_full_text):
                    is_matched = True

        if is_matched and skill not in matched_skills:
            matched_skills.append(skill)

    return matched_skills


def main():
    test_cases = [
        "",
        " ",
        "a",
        "Looking for a Full Stack Developer proficient in Python, React, PostgreSQL, Docker, and REST API development. Experience with Git and CI/CD pipelines is required.",
        "Urgent requirement for EV Battery Systems Engineer experienced in Electric Vehicle Battery Management, Battery Chemistry, MATLAB Simulink, and CAN Bus Diagnostics.",
        "Hiring Specialist for Digital Textile Printing, Sublimation Printing, Color Fastness Testing, Fabric Inspection, and RIP Software.",
        None,
    ]

    print("=== Testing Skill Extractor ===")
    for idx, case in enumerate(test_cases, 1):
        extracted = extract_skills(case)
        print(f"\nTest {idx}: {case!r}")
        print(f"Extracted ({len(extracted)} skills): {extracted}")


if __name__ == "__main__":
    main()
