import os
import re
import sys
from pathlib import Path

# Paths to scan
PATHS_TO_SCAN = ["backend/app", "backend/research", "apps/web/src"]

# Regex patterns to search for
BANNED_PATTERNS = {
    "SECRET_POSTGRES": re.compile(r"postgresql(\+[^:]+)?://[^:]+:[^@]+@"),
    "SECRET_SK": re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
    "SECRET_AIZA": re.compile(r"\bAIza[a-zA-Z0-9_-]{35}\b"),
    "SECRET_RZP_LIVE": re.compile(r"\brzp_live_[a-zA-Z0-9]+\b"),
    "SECRET_LLM_ENV": re.compile(r"LLM-ENV"),
    "HARDCODED_WINDOWS_PATH": re.compile(
        r"(?:^|(?<![A-Za-z0-9]))[A-Za-z]:[/\\]|(?:^|(?<![A-Za-z0-9]))\\\\[^\\/]+[\\/]",
        re.IGNORECASE,
    ),
    "CREATE_ALL": re.compile(r"create_all\("),
    "SQLITE3_CONNECT": re.compile(r"sqlite3\.connect\("),
    "MATH_RANDOM": re.compile(r"Math\.random\("),
}

ALLOW_COMMENT = re.compile(r"#\s*honesty:\s*allow")
ALLOW_COMMENT_JS = re.compile(r"//\s*honesty:\s*allow")

def check_file(filepath):
    violations = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                if ALLOW_COMMENT.search(line) or ALLOW_COMMENT_JS.search(line):
                    continue
                for name, pattern in BANNED_PATTERNS.items():
                    # Math.random is only checked in JS/TS files
                    if name == "MATH_RANDOM" and not filepath.name.endswith((".ts", ".tsx", ".js", ".jsx")):
                        continue
                    if pattern.search(line):
                        violations.append((line_idx + 1, name, line.strip()))
    except Exception as e:
        # Ignore decoding errors for non-text files that slipped through
        pass
        
    return violations

def main():
    root_dir = Path(__file__).resolve().parent.parent
    all_violations = []

    for scan_dir in PATHS_TO_SCAN:
        dir_path = root_dir / scan_dir
        if not dir_path.exists():
            continue
            
        for root, _, files in os.walk(dir_path):
            for file in files:
                # skip non-text extensions generally
                if file.endswith((".png", ".jpg", ".zip", ".pyc", ".db", ".sqlite")):
                    continue
                    
                filepath = Path(root) / file
                violations = check_file(filepath)
                for v in violations:
                    all_violations.append((filepath, v[0], v[1], v[2]))

    if all_violations:
        print("[X] HONESTY GUARD VIOLATION(S) FOUND:")
        for v in all_violations:
            rel_path = v[0].relative_to(root_dir)
            print(f"  {rel_path}:{v[1]} [{v[2]}] - {v[3][:80]}")
        sys.exit(1)
    else:
        print("honesty guard: clean")
        sys.exit(0)

if __name__ == "__main__":
    main()
