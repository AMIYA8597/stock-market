# Secrets Rotation Checklist

**IMPORTANT:** You must execute this checklist manually. An AI agent cannot log into your Supabase or broker dashboards to rotate keys.

| Component | Instructions | Verified Rotated On |
| :--- | :--- | :--- |
| **Supabase DB Password (DEV)** | 1. Go to Supabase Dashboard > Project Settings > Database.<br>2. Click "Reset Database Password".<br>3. Generate a new strong password and save it in your secure local `.env`. | `[ ]` |
| **Supabase DB Password (PROD)** | Same as above, for your PROD project. | `[ ]` |
| **Supabase API Keys / JWT Secret** | 1. Go to Supabase Dashboard > Project Settings > API.<br>2. Roll the JWT Secret. This invalidates the old `anon` and `service_role` keys.<br>3. Generate new keys and update your `.env`. | `[ ]` |
| **Provider API Keys** | Re-issue every key that was present in `LLM-ENVVV-ALL-KEYS-.txt` or `apps/web/llm-env.txt`. This includes any broker tokens (Upstox, Angel One), FRED keys, or LLM keys (OpenAI/Anthropic). | `[ ]` |
| **nq_api Role Password** | 1. Connect to the DB as `postgres`.<br>2. Run `ALTER ROLE nq_api WITH PASSWORD 'new_strong_password';`.<br>3. Update your API environment variables. | `[ ]` |
| **Broker Tokens** | Revoke any Upstox/AngelOne tokens from their respective developer dashboards and generate new ones. | `[ ]` |
