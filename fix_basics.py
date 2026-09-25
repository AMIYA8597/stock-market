import os
import re

path = 'backend/app/main.py'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Simple replace
    text = text.replace('return {"status": "ok"}', 'return {"status": "running"}')
    text = text.replace('"pymongo", "motor", ', '')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

path = 'backend/app/core/logging.py'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = re.sub(r'logging.getLogger\("pymongo"\).setLevel.*?\n', '', text)
    text = re.sub(r'logging.getLogger\("motor"\).setLevel.*?\n', '', text)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
        
path = 'services/gateway/app/main.py'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    text = text.replace('"status": "ok"', '"status": "running"')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

