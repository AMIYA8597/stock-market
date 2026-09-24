import re

with open('backend/app/api/v1/websocket_url.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('router = APIRouter()', 'router = APIRouter(prefix="/websocket_url")')

with open('backend/app/api/v1/websocket_url.py', 'w', encoding='utf-8') as f:
    f.write(text)
