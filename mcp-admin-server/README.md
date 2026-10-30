# orange-admin MCP server

Exposes the Orange platform's admin API as tools an AI agent (AnythingLLM's
`@agent`) can call — live usage, feedback, provider health, PII rules, token
governance. Standalone from `backend/`: talks to the running Flask app over
HTTP, the same way any admin client would.

## Tools

### Reads — plain GETs, call freely

- `list_companies()` — every tenant: id, name, domain, caps, Qdrant isolation
- `list_providers()` — every LLM provider: enabled, priority, rate limits, key set?
- `get_usage_summary(company_name?, provider_name?, since?)` — token/request totals + breakdowns
- `get_feedback_summary(company_name?, provider_name?, since?)` — thumbs up/down, satisfaction score, review queue
- `list_pii_rules(company_name?)` — custom PII regex rules (global + that company's)
- `list_ingestions(company_name?)` — KB add-document audit trail
- `list_deletions(company_name?)` — KB remove-document audit trail
- `qdrant_pool_status()` — dedicated Qdrant instances: who claims each, how many free
- `list_token_requests(status?)` — "raise my limit" requests; filter pending/approved/rejected

### Diagnostics — read-only, but the tool does the multi-step work

- `health_check_all_providers(include_disabled?)` — probes every provider in turn, returns live/degraded/down per provider with round-trip time
- `diagnose_company(company_name)` — one-call health report: caps vs. 24h usage, feedback score, blocked-chunk ingestions, empty-KB check → flags + verdict
- `find_problem_providers(since?)` — ranks providers worst-first by feedback score + disabled state

### Writes — dry-run unless `confirm=true`

Each returns a preview (`dry_run: true`, `would_change: {...}`) on a bare call
and only mutates when re-called with `confirm=true`. The guard lives in this
server, not the backend.

- `set_provider_enabled(provider_name, enabled, confirm?)` — take a provider in/out of the fallback chain
- `create_pii_rule(entity_name, pattern, company_name?, score?, confirm?)` — add a redaction regex (validated locally first)
- `set_company_token_limit(company_name, daily_token_limit, confirm?)` — company pool cap (`null` = uncapped)
- `set_user_token_limit(email, daily_token_limit, confirm?)` — personal cap (`0` = blocked, `null` = platform default)
- `decide_token_request(request_id, decision, reason?, confirm?)` — approve/reject a pending request
- `test_provider(provider_name)` — actively probe one provider now

## Prompt + resources

- prompt `platform_admin_briefing` — starting brief for the agent (the three tiers, work-in-names, dry-run etiquette)
- resource `orange://providers`, `orange://companies` — live registry reads the agent gets without a tool call

## Requirements

- `backend/`'s Flask app running (`python run.py`, default `http://localhost:5000`)
- A super_admin account's email/password (dev seed: `admin@orange.com` / `password123`,
  see `backend/app/seed.py`)

## Registered with AnythingLLM Desktop

Already added to:
`%APPDATA%\anythingllm-desktop\storage\plugins\anythingllm_mcp_servers.json`

AnythingLLM auto-starts this script whenever you open the Agent Skills page
or type `@agent` in a chat — no need to run it manually. It logs in once
(caching the JWT) and re-logs in automatically if the token expires.

## Running it manually (for testing outside AnythingLLM)

PowerShell:
```powershell
cd mcp-admin-server
$env:ORANGE_ADMIN_EMAIL = "admin@orange.com"
$env:ORANGE_ADMIN_PASSWORD = "password123"
./.venv/Scripts/python.exe server.py
```

Bash/Git Bash:
```bash
cd mcp-admin-server
ORANGE_ADMIN_EMAIL=admin@orange.com ORANGE_ADMIN_PASSWORD=password123 ./.venv/Scripts/python.exe server.py
```

This starts the stdio MCP server and waits for a client (like AnythingLLM) to
connect — it won't print anything on its own if nothing's talking to it yet.

## Security note

The AnythingLLM config file above stores the admin password in plaintext,
local to this machine — same exposure as the seed script itself (which
already prints it to the console and hardcodes it as dev-only). If this is
ever pointed at a real production admin account instead of the dev seed,
that file should be treated accordingly (it lives outside this repo, in
AnythingLLM's own AppData folder, so it won't get committed by accident).

The write tools' `confirm=true` guard is a UX safety net against an agent
acting on a half-understood request — it is **not** an authorization boundary.
Anything this server can do, it does with full super_admin rights.
