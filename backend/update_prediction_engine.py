import re

with open("app/services/prediction_engine.py", "r") as f:
    code = f.read()

# We want to replace from:
#     # Prepare DataFrame by running all builders and indicators
#     df.index = pd.DatetimeIndex(df["time"])
# ...
#     for col in [
#         "sentiment_score",
# ...
#         if col not in df.columns:
#             df[col] = 0.0
# with the new build_features call.

pattern = re.compile(r'    # Prepare DataFrame by running all builders and indicators.*?            df\[col\] = 0\.0', re.DOTALL)

replacement = """    # -------------------------------------------------------------
    # NEW POINT-IN-TIME FEATURE LIBRARY CALL (Part 3 V2-3)
    # -------------------------------------------------------------
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from research.feature_engineering.api import build_features

    df = build_features(df, mode="serving")
    # -------------------------------------------------------------"""

if pattern.search(code):
    print("Found pattern, replacing...")
    new_code = pattern.sub(replacement, code)
    with open("app/services/prediction_engine.py", "w") as f:
        f.write(new_code)
else:
    print("Pattern not found!")

