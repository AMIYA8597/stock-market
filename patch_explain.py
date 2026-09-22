import re

with open('backend/app/api/v1/explain.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 503 instead of fake response
replacement = '''        if not artifact:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse.create(
                    code="MODEL_NOT_TRAINED",
                    message=f"No active artifact found for {symbol}.",
                ).dict(),
            )

        # 1. Fetch live prediction
        result = await get_full_prediction(
            symbol,
            bypass_cache=False,
            artifact_path=artifact.artifact_path,
            model_version=artifact.version_tag,
        )
        if not result or not result.get("is_computed", False):
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse.create(
                    code="MODEL_NOT_TRAINED",
                    message=f"No prediction found for {symbol}.",
                ).dict(),
            )'''
content = re.sub(
    r'        if not artifact:.*?return SHAPResponse.*?timestamp=datetime\.now\(UTC\),\s*\).*?if not result or not result\.get\("is_computed", False\):.*?return SHAPResponse.*?timestamp=datetime\.now\(UTC\),\s*\)',
    replacement,
    content,
    flags=re.DOTALL
)

# 2. Remove substring guessed feature values
substring_guess_regex = r'# Resolve actual feature value from the prediction results.*?# Compute a deterministic percentile rank \[0\.0, 100\.0\].*?pct_rank = 10\.0 \+ 80\.0 / \(1\.0 \+ math\.exp\(-feat_val \* 10\.0\)\)'
content = re.sub(
    substring_guess_regex,
    'feat_val = float(feat.get("value", 0.0))\n            pct_rank = 50.0',
    content,
    flags=re.DOTALL
)

with open('backend/app/api/v1/explain.py', 'w', encoding='utf-8') as f:
    f.write(content)
