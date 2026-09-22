import re

with open('backend/app/services/intelligence_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'    def get_drift\(self\) -> list\[DriftItem\]:.*?    def get_ensemble_weights_history',
    '    def get_drift(self) -> list[DriftItem]:\n        return []\n\n    def get_ensemble_weights_history',
    content,
    flags=re.DOTALL
)

with open('backend/app/services/intelligence_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
