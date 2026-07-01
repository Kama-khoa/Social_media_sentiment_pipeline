import sqlite3
import requests
from dotenv import load_dotenv
load_dotenv()

conn = sqlite3.connect('data/web_app.db')
c = conn.cursor()
c.execute("SELECT email FROM app_users WHERE role='admin' LIMIT 1")
admin_email = c.fetchone()[0]

res = requests.post('http://localhost:8000/auth/login', json={'email': admin_email, 'password': 'password123'})
token = res.json().get('access_token')

res2 = requests.post(
    'http://localhost:8000/admin/products/detail-requests/a81cae8d-05ee-4824-b953-d8ba62bf163c/review',
    json={'action':'approve'},
    headers={'Authorization': f'Bearer {token}'}
)
print('STATUS:', res2.status_code)
print('BODY:', res2.text)
