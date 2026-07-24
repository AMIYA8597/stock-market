
path = r"d:\work\stock-market\backend\app\services\prediction_engine.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Fix UnboundLocalError by removing import numpy as np inside the function
content = content.replace("    import numpy as np\n", "")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
