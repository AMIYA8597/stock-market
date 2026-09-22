import re

with open('backend/app/services/prediction_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'\s*except Exception as ee:\s*logger\.error\(f"ExponentialSmoothing fallback also failed: \{ee\}"\)\s*current = float\(closes\[-1\]\)\s*pred_mean = np\.full\(steps, current\)\s*pred_ci = np\.column_stack\(\[pred_mean \* 0\.97, pred_mean \* 1\.03\]\)\s*return pred_mean, pred_ci',
    '',
    content,
    flags=re.DOTALL
)

with open('backend/app/services/prediction_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
