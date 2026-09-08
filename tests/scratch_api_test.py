import requests, os
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.env'))
app_id  = os.getenv('ADZUNA_APP_ID','')
app_key = os.getenv('ADZUNA_APP_KEY','')
print(f'APP_ID  len={len(app_id)}  value={app_id}')
print(f'APP_KEY len={len(app_key)}')

url = 'https://api.adzuna.com/v1/api/jobs/in/search/1'
params = {
    'app_id': app_id,
    'app_key': app_key,
    'results_per_page': 5,
    'what': 'Python developer',
    'where': 'Pune',
    'content-type': 'application/json'
}
try:
    r = requests.get(url, params=params, timeout=12)
    print(f'Adzuna HTTP Status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        count = data.get('count', 0)
        print(f'Results returned: {count}')
        print('PASS  Adzuna API working correctly')
    else:
        print(f'Response body (first 400 chars): {r.text[:400]}')
        print('FAIL  API returned non-200')
except Exception as e:
    print(f'FAIL  Exception: {e}')
