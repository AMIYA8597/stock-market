import re

with open('backend/app/services/intelligence_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'    def get_model_accuracy\(self\) -> list\[ModelAccuracyItem\]:.*?return rows',
    '',
    content,
    flags=re.DOTALL
)

with open('backend/app/services/intelligence_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
