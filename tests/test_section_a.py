import sys, importlib, os

print('--- A1: Packages ---')
pkgs = ['streamlit', 'pandas', 'spacy', 'sklearn', 'dotenv', 'rapidfuzz', 'requests']
for p in pkgs:
    mod = importlib.import_module(p)
    print(f'  {p}: {getattr(mod, "__version__", "installed")}')

print('--- A2: spaCy Model ---')
import spacy
nlp = spacy.load('en_core_web_sm')
print(f'  en_core_web_sm loaded successfully, pipeline: {nlp.pipe_names}')

print('--- A3: Files ---')
files = [
    'data/jobs_sample.csv',
    'data/curriculum_sample.csv',
    'src/load_data.py',
    'src/skill_extractor.py',
    'src/demand_scorer.py',
    'src/gap_detector.py',
    'app/dashboard.py',
    '.env',
    'requirements.txt',
    'README.md'
]
for f in files:
    assert os.path.exists(f), f'Missing file: {f}'
    print(f'  {f}: EXISTS')

print('--- A4: .env Variables ---')
from dotenv import load_dotenv
load_dotenv('.env')
app_id = os.getenv('ADZUNA_APP_ID', '')
app_key = os.getenv('ADZUNA_APP_KEY', '')
print(f'  ADZUNA_APP_ID: {"PRESENT (len=" + str(len(app_id)) + ")" if app_id else "EMPTY"}')
print(f'  ADZUNA_APP_KEY: {"PRESENT (len=" + str(len(app_key)) + ")" if app_key else "EMPTY"}')
assert app_id and app_key, 'Adzuna keys missing or empty!'
print('\n>>> SECTION A: ALL CHECKS PASS <<<')
