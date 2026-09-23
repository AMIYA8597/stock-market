import os
from dotenv import load_dotenv
load_dotenv('.env')
os.system('alembic revision -m "Add RLS policies"')
