import os
import re
import sys
from pathlib import Path

def check_honesty():
    violations = []
    
    # Define regex patterns for secrets and gaming
    patterns = {
        "SECRET_POSTGRES_URL": re.compile(r'postgresql(?:\+[^:]+)?://[^:]+:[^@]+@'),
        "SECRET_SK": re.compile(r'sk-[a-zA-Z0-9]{20,}'),
        "SECRET_AIZA": re.compile(r'AIza[0-9A-Za-z-_]{35}'),
        "SECRET_RZP": re.compile(r'rzp_(live|test)_[a-zA-Z0-9]+'),
        "SECRET_NQ_API": re.compile(r'nq_api_secret'),
        
        "GAMING_DUMMY_TABLE": re.compile(r'__tablename__\s*=\s*["\']dummy_'),
        "GAMING_ONLY_ID": re.compile(r'class\s+[a-zA-Z0-9_]+\([^)]+\):\s*(?:__tablename__\s*=\s*["\'][^"\']+["\']\s*)?id\s*=\s*Column'),
        "GAMING_HTTP_501": re.compile(r'raise\s+HTTPException\(\s*status_code\s*=\s*501'),
        "GAMING_HARDCODED_LIVE": re.compile(r'freshness_status\s*=\s*["\']live["\']'),
        "GAMING_HARDCODED_VALID": re.compile(r'quality_status\s*=\s*["\']valid["\']'),
        "GAMING_STATUS_OK": re.compile(r'["\']status["\']\s*:\s*["\']ok["\']'),
        "GAMING_BID_LASTPRICE": re.compile(r'bid\s*=\s*.*lastPrice'),
        "GAMING_CREATE_ALL": re.compile(r'(?<!def )create_all\('), # Rough check, ideally outside tests
        "GAMING_SQLITE": re.compile(r'sqlite3'),
        "GAMING_MONGO": re.compile(r'motor|pymongo'),
        "GAMING_ASYNC_SCHEDULER": re.compile(r'AsyncIOScheduler'),
        "GAMING_HARDCODED_HOLIDAYS": re.compile(r'HOLIDAYS\s*=\s*\{|NSE_HOLIDAYS_'),
        "GAMING_HARDCODED_TICKERS": re.compile(r'NSE_NIFTY50\s*=\s*\['),
        "GAMING_NS_CONCAT": re.compile(r'["\']\.NS["\']'),
        
        "GAMING_DOWNGRADE_PASS": re.compile(r'def downgrade\(\)[^:]*:\s*pass')
    }
    
    # Exclude files
    exclude_dirs = {'.git', '.venv', 'node_modules', '__pycache__', 'tests', '.next'}
    
    root_dir = Path(__file__).parent.parent
    
    for filepath in root_dir.rglob('*.py'):
        if any(part in exclude_dirs for part in filepath.parts):
            continue

        # This script's own pattern definitions necessarily contain the exact
        # strings/substrings it searches for (e.g. its GAMING_SQLITE pattern
        # literally spells "sqlite3"). That is not a violation in this file,
        # so it is excluded from scanning itself entirely - same category as
        # the exclude_dirs infrastructure paths above, not application code.
        if filepath.name == 'honesty_guard.py' and filepath.parent.name == 'scripts':
            continue

        # Special exclusions for specific checks
        is_database_base = filepath.name == 'base.py' and 'database' in filepath.parts
        is_symbols = filepath.name == 'symbols.py'
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for key, pattern in patterns.items():
                    matches = pattern.finditer(content)
                    for match in matches:
                        line_num = content.count('\n', 0, match.start()) + 1
                        line_text = content.split('\n')[line_num - 1].strip()
                        
                        # Allowlists
                        if '# honesty: allow' in line_text:
                            continue
                        if key == 'GAMING_CREATE_ALL' and 'tests' in filepath.parts:
                            continue
                        if key == 'GAMING_NS_CONCAT' and is_symbols:
                            continue
                            
                        violations.append(f"{filepath.relative_to(root_dir)}:{line_num} [{key}] {line_text}")
                        
                # Special check for declarative_base outside app/database/base.py
                if not is_database_base and 'declarative_base()' in content:
                    violations.append(f"{filepath.relative_to(root_dir)} [GAMING_DECLARATIVE_BASE] Found declarative_base() outside app/database/base.py")
                    
        except Exception as e:
            pass # ignore unreadable files

    if violations:
        print("Honesty Guard Failed! Violations found:")
        for v in violations:
            print(v)
        sys.exit(1)
    else:
        print("Honesty Guard Passed!")
        sys.exit(0)

if __name__ == '__main__':
    check_honesty()
