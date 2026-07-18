#!/usr/bin/env python3
"""Repository audit script for NeuroQuant project.
Generates a JSON report (artifacts/repo_audit.json) containing:
- File tree
- Unused Python modules (no import elsewhere)
- Duplicate filenames
- TODO/FIXME markers
- Potential secrets (regex patterns)
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

report = {
    "file_tree": {},
    "unused_python_modules": [],
    "duplicate_filenames": {},
    "todo_fixme": [],
    "potential_secrets": []
}

# Build file tree
for dirpath, dirnames, filenames in os.walk(ROOT):
    rel_dir = os.path.relpath(dirpath, ROOT)
    if rel_dir.startswith('.git') or rel_dir.startswith('node_modules') or rel_dir.startswith('artifacts'):
        continue
    report["file_tree"][rel_dir] = filenames

# Gather all python files
python_files = []
for path in ROOT.rglob('*.py'):
    if 'node_modules' in str(path) or '.git' in str(path) or 'artifacts' in str(path):
        continue
    python_files.append(path)

# Find imports
imported_modules = set()
for py in python_files:
    try:
        with open(py, 'r', encoding='utf-8') as f:
            for line in f:
                m = re.match(r"\s*import\s+([a-zA-Z0-9_]+)", line)
                if m:
                    imported_modules.add(m.group(1))
                m = re.match(r"\s*from\s+([a-zA-Z0-9_]+)\s+import", line)
                if m:
                    imported_modules.add(m.group(1))
    except Exception:
        continue

# Determine unused modules (module name equals file stem)
for py in python_files:
    module_name = py.stem
    if module_name not in imported_modules and module_name != "__init__":
        report["unused_python_modules"].append(str(py.relative_to(ROOT)))

# Duplicate filenames (different directories)
name_counts = {}
for py in python_files:
    name = py.name
    name_counts.setdefault(name, []).append(str(py.relative_to(ROOT)))
for name, locations in name_counts.items():
    if len(locations) > 1:
        report["duplicate_filenames"][name] = locations

# TODO/FIXME markers
todo_pattern = re.compile(r"#\s*(TODO|FIXME):?")
for file_path in ROOT.rglob('*'):
    if file_path.is_file():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if todo_pattern.search(line):
                        report["todo_fixme"].append({"file": str(file_path.relative_to(ROOT)), "line": i, "text": line.strip()})
        except Exception:
            continue

# Potential secrets (simple regex for AWS keys, private keys)
secret_patterns = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN PRIVATE KEY-----"),
    re.compile(r"password\s*=\s*['\"]?[^'\"]+['\"]?")
]
for file_path in ROOT.rglob('*'):
    if file_path.suffix not in ['.py', '.js', '.json', '.yaml', '.yml', '.env', '.txt']:
        continue
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for pat in secret_patterns:
                if pat.search(content):
                    report["potential_secrets"].append(str(file_path.relative_to(ROOT)))
                    break
    except Exception:
        continue

# Write report
out_path = ARTIFACTS_DIR / "repo_audit.json"
with open(out_path, 'w', encoding='utf-8') as out:
    json.dump(report, out, indent=2)

print(f"Audit report written to {out_path}")
