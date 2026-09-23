import os
from dotenv import load_dotenv
load_dotenv('.env')
os.system('alembic revision --autogenerate -m "Stage 1 init"')
