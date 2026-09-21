import os, re
for filename in ["backend/scripts/test_e2e_prediction.py", "backend/scripts/test_shap_consistency.py"]:
    with open(filename, "r") as f:
        content = f.read()
    
    new_path = "os.path.abspath(os.path.join(os.path.dirname(__file__), \"../data/artifacts/xgboost_A_6d8d915f.pkl\"))"
    
    if "import os" not in content:
        content = "import os\n" + content
        
    content = content.replace("\"D:/work/stock-market/backend/data/artifacts/xgboost_A_6d8d915f.pkl\"", new_path)
    
    with open(filename, "w") as f:
        f.write(content)
