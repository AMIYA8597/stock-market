import os
import subprocess

def run_cmd(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True)

# 1. Identify patch_*.py files
patch_files = subprocess.check_output("git ls-files | findstr /i patch_", shell=True).decode('utf-8').splitlines()
for f in patch_files:
    run_cmd(f'git rm -f "{f}"')

# 2. Identify and remove specific files
specific_files = [
    "apps/web/llm-env.txt",
    "LLM-ENVVV-ALL-KEYS-.txt",
    "scripts/build_dummy_models.py",
    "backend/setup_roles.py"
]

for f in specific_files:
    if os.path.exists(f):
        run_cmd(f'git rm -f "{f}"')

# 3. Identify loose root-level scripts/dumps (anything .py or .json in root, except maybe main.py if it existed)
root_files = subprocess.check_output("git ls-files", shell=True).decode('utf-8').splitlines()
for f in root_files:
    if '/' not in f:
        # It's a root level file
        if f.endswith('.py') or f.endswith('.json') or f.endswith('.txt') or f.endswith('.patch') or 'KEY' in f or 'llm-env' in f:
            if f not in ['pytest.ini', 'package.json', 'tsconfig.json', 'turbo.json', 'requirements.txt', 'README.md']:
                print(f"Removing loose root file: {f}")
                run_cmd(f'git rm -f "{f}"')

# 4. Remove backend/test_*.py outside tests/
backend_files = subprocess.check_output("git ls-files backend", shell=True).decode('utf-8').splitlines()
for f in backend_files:
    if f.startswith('backend/test_') and f.endswith('.py'):
        run_cmd(f'git rm -f "{f}"')
    if f.startswith('backend/logs/') or f.startswith('backend/datasets/'):
        run_cmd(f'git rm -f "{f}"')

print("Done cleaning.")
