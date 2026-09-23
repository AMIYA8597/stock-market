import psycopg2, os
from dotenv import load_dotenv
load_dotenv('backend/.env')
url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg', 'postgresql').replace('ssl=require', 'sslmode=require')
print(url)
try:
    conn = psycopg2.connect(url, connect_timeout=10)
    print("Connected")
except Exception as e:
    print("Error:", e)
