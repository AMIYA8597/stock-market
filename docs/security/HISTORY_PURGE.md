# Repository History Purge Procedure

**IMPORTANT: This procedure must be executed by a human.**

The repository's git history contains plaintext secrets (API keys, Supabase Postgres credentials, MongoDB URIs) that were accidentally tracked. Rotating the keys is the primary defense, but we also must purge the leaked files from the entire git history to keep the repository safe and reduce bloat.

## Requirements
You must have Python installed. The `git-filter-repo` tool is the modern, safe replacement for `git filter-branch` and BFG.

## Step-by-Step Instructions

1. **Install git-filter-repo** using `uv` or `pip`:
   ```bash
   uv tool install git-filter-repo
   ```

2. **Create a fresh, bare mirror clone** of your repository (this prevents issues with your local working tree):
   ```bash
   cd ..
   git clone --mirror <YOUR_REPO_URL> stock-market-mirror
   cd stock-market-mirror
   ```

3. **Run the history filter** to completely invert (remove) the paths of the exposed files:
   ```bash
   git filter-repo --invert-paths \
     --path scripts/test_supabase.py \
     --path LLM-ENVVV-ALL-KEYS-.txt \
     --path gitleaks.zip \
     --path gitleaks_bin \
     --path full_diff.patch \
     --path diff_utf8.patch \
     --path history_resp.json
   ```

4. **Verify the purge** with `gitleaks` (if available):
   ```bash
   gitleaks detect --no-banner
   # Ensure no leaks are detected in the repository history
   ```

5. **Force-push the changes** to the remote repository:
   ```bash
   git push origin --force --all
   git push origin --force --tags
   ```

6. **Coordinate with your team**
   Every developer must re-clone the repository from scratch. Old clones will contain the tainted history and if someone pushes from an old clone, the leaked files might be reintroduced.

---
**CRITICAL WARNING:** Purging history does **NOT** revoke access to compromised systems. All keys and passwords found in the repository (e.g. Supabase, MongoDB, APIs) **must still be rotated** following the checklist in `docs/security/ROTATION_CHECKLIST.md`.
