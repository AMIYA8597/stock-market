# Git History Purge Procedure

**IMPORTANT:** Rotating secrets is required *regardless* of purging history. History purging only protects against future exposure, not past exposure to anyone who has already cloned the repo or scanned it.

## Prerequisites
You need the `git-filter-repo` tool.
```powershell
uv tool install git-filter-repo
```

## Procedure
1. Create a fresh mirror clone of the repository (do NOT do this in your active working directory):
   ```powershell
   git clone --mirror https://github.com/YOUR_ORG/stock-market.git
   cd stock-market.git
   ```

2. Run `git-filter-repo` to remove the offending files from the entire history:
   ```powershell
   git filter-repo --invert-paths `
     --path "scripts/test_supabase.py" `
     --path "LLM-ENVVV-ALL-KEYS-.txt" `
     --path "apps/web/llm-env.txt" `
     --path "backend/setup_roles.py" `
     --path-glob "gitleaks*" `
     --path-glob "*.patch" `
     --path "history_resp.json"
   ```

3. Verify the purge was successful using `gitleaks`:
   ```powershell
   gitleaks detect --no-banner
   ```

4. Force-push the rewritten history back to the remote:
   ```powershell
   git push origin --force --all
   git push origin --force --tags
   ```

5. Instruct all collaborators to delete their local clones and re-clone the repository from scratch. Attempting to `git pull` on an old clone will merge the corrupted history back in.
