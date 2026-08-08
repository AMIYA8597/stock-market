# Security Notes

## Executive Posture Summary
Following the exhaustive S-Series Security Audit (Phases S0-S7), the application's API and database layers are heavily fortified against modern web vulnerabilities. We have confirmed the integrity of authentication, authorization, cryptography, rate limiting, and webhook validation.

## Hardened Surfaces
1. **Broken Object Level Authorization (BOLA/BFLA)**: All API routes strictly filter by `id` AND the authenticated `user_id`. Cross-user data access is structurally prevented at the database query level.
2. **Cryptographic Primitives**: JWT implementation rigidly enforces the RS256 algorithm and rejects `alg: none`. 2FA Secrets (TOTP) are encrypted at rest using Fernet symmetric encryption.
3. **Transport & Injection**: Global middleware guarantees Strict-Transport-Security (HSTS), CSP, and X-Content-Type-Options headers on all responses. Raw SQL is unused; the system utilizes SQLAlchemy ORM bound parameters and Pydantic boundary validation exclusively.
4. **Rate Limiting & Abuse**: Aggressive rate limiting exists on `/login`, `/register`, `/forgot-password`, and expensive inference endpoints via a Redis Token Bucket, mitigating credential stuffing and DoS attacks.
5. **Webhook Integrity**: Razorpay webhooks rigorously validate HMAC-SHA256 signatures in production, neutralizing spoofing attempts.

## Secret Handling Process
- `.env` files are correctly gitignored and MUST NOT be committed to the repository.
- `.env.example` contains ONLY placeholder values and is committed to serve as a template.
- The repository is actively scanned for secrets using `gitleaks` via a pre-commit hook and CI checks.

> [!WARNING]
> **Important:** Any future manual zip/archive export of this repository MUST exclude `.env` files. Even though they are ignored by git, a manual copy or zip command (e.g., `zip -r archive.zip .`) may accidentally bundle them, leading to secret leakage. Always verify the contents of an archive before sharing it.

## Dependency & CI Baseline (Accepted Risks)
The repository enforces continuous security scanning via `.github/workflows/security.yml`.
The pipeline will automatically **fail** if any of the following are detected:
- New high or critical dependency vulnerabilities via `pip-audit` or `pnpm audit`.
- High severity static code analysis vulnerabilities via `bandit`.
- Hardcoded secrets via `gitleaks`.

**Current Exceptions (Accepted Baselines)**:
1. **Frontend (Next.js/Turbo)**: Certain Cache Poisoning and SSR DoS vulnerabilities (e.g., `GHSA-3g8h-86w9-wvmq`, `GHSA-qpjv-v59x-3qc4`) affecting Next.js 14 are baselined and ignored via `pnpm.auditConfig.ignoreCves` in `package.json`. These will be addressed during a dedicated major-version upgrade (Next.js 15 / React 19).
2. **Backend (Bandit)**: The `B301` Pickle deserialization warnings in `backend/research/models/` are safely ignored via the `.bandit` config, as these models are generated internally by researchers and do not parse untrusted user data.
3. **Backend (XML Parsing)**: `B314` XML vulnerabilities in `app/services/sentiment_analyzer.py` are ignored inline using `# nosec B314` as the endpoints only fetch data from trusted public RSS feeds over HTTPS.

## Recommended Re-Audit Cadence
To maintain this security posture, the following cadence is recommended:
- **Monthly**: Review CI Dependency Audit logs to identify newly disclosed zero-days affecting standard libraries.
- **On New Resource Creation**: Whenever a new entity (e.g., a new type of trade, an invoice, a user preference) is added to the database, explicitly write a BOLA test to guarantee it filters by `user_id`.
- **Quarterly**: Re-evaluate the baselined Next.js CVEs to determine if an upgrade path is stable enough to pursue.
