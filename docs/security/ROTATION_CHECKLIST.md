# Security Rotation Checklist

**IMPORTANT:** Do NOT check off these items until you have actually completed them in the respective vendor dashboards.

## 1. Supabase (DEV and PROD Projects)
- [ ] **Reset Database Password:** Go to Project Settings → Database → Reset Database Password.
- [ ] **Roll API Keys:** Go to Project Settings → API. Roll/replace both the `anon/public` and `service_role` keys.
- [ ] **Generate new JWT Secret:** Go to Project Settings → API → JWT Settings → Generate a new secret.
- [ ] **Review Auth Users:** Go to Authentication → Users. Look for any unrecognized or unauthorized accounts.
- [ ] **Review Database Roles:** Go to Database → Roles. Ensure no unauthorized roles have been created.
- [ ] **Check Logs for Unauthorized Access:** Go to Database → Logs / Auth logs. Check for any unknown IPs connecting since the leak commit date (`9cae49e`). 
    - *Findings/Notes:* ___________________________________________

## 2. Third-Party Services (From LLM-ENVVV-ALL-KEYS-.txt and .env)
Revoke and re-issue the following keys (if applicable):
- [ ] **OpenRouter:** Revoke old key and generate a new one.
- [ ] **Google AI Studio / Gemini:** Revoke old API key and generate a new one.
- [ ] **MongoDB Atlas:** Change the database user password (Project Settings → Database Access).
- [ ] **Razorpay:** Roll test keys (Settings → API Keys → Regenerate).
- [ ] **Resend / Email Provider:** Roll API keys.
- [ ] **OpenAI:** Revoke old key, issue new one.
- [ ] **DeepSeek:** Revoke old key, issue new one.
- [ ] **HuggingFace:** Revoke old token, issue new one.

*Note: You must perform this rotation immediately. History purge alone does NOT protect exposed credentials.*
