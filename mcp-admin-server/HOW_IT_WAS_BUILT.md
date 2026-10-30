# How the `orange-admin` MCP server was built

A narrative, decision-by-decision account of the MCP integration — written to be
read top to bottom, no code reading required. Companion to `README.md` (which is
the quick reference) and `server.py` (the implementation).

---

## 1. The problem this solves

The Orange project is a **multi-tenant Retrieval-Augmented-Generation platform**:
a Flask backend + Angular frontend that gives each customer company its own
chat assistant grounded in that company's uploaded documents, with an admin layer
for usage quotas, LLM-provider routing, PII redaction rules and per-tenant vector
isolation (shared vs. dedicated Qdrant).

The supervisor's brief was short: *"use AnythingLLM, it's easy, implement it."*
No specific feature was named. So the first real task was deciding **what job to
give AnythingLLM** that would add something the hand-built platform doesn't
already do.

AnythingLLM out of the box already provides:

| AnythingLLM feature | The platform already has its own |
| --- | --- |
| Chat UI | Angular chat shell |
| Document upload + RAG | Flask ingestion pipeline + Qdrant retrieval |
| Multiple LLM providers | `llm_router.py` with fallback + rate limiting |
| Workspaces | Per-company tenancy |

Duplicating any of that would just be a second, worse copy. The **one thing
AnythingLLM has that the platform genuinely lacks is an agent** — a loop where an
LLM decides which tools to call, in what order, reading each result before
choosing the next step (`@agent` in a chat, or the *Agent Skills* page).

So the integration is: **keep the platform's own portal for chat/RAG, and use
AnythingLLM purely as an agent front-end that can *operate* the platform** —
answer "is anything broken", "why are BIAT's answers bad", "raise FIAT's quota" —
by calling the admin API as tools.

That tool bridge is this MCP server.

---

## 2. What MCP is (30-second version)

**Model Context Protocol** is a small JSON-RPC protocol that lets an LLM host
(Claude Desktop, AnythingLLM, Cursor, …) discover and call external capabilities
without any host-specific plugin code. A *server* exposes three kinds of thing:

- **tools** — functions the model can call (name, JSON-schema arguments, description)
- **resources** — readable blobs addressed by URI, injected as context
- **prompts** — reusable prompt templates the user can pick

The host launches the server as a subprocess and talks to it over **stdio**
(stdin/stdout carrying JSON-RPC messages). No network port, no HTTP, no
registration with a central registry. The host calls `tools/list` once to learn
what's available, then `tools/call` each time the model wants to use one.

The practical payoff: the same server works in AnythingLLM today and in Claude
Desktop tomorrow with a one-line config change.

---

## 3. Architecture decision: standalone HTTP client, *not* a backend import

The server could have imported `backend/app` directly and called service
functions in-process. It deliberately doesn't. It runs as its own tiny project
(`mcp-admin-server/`, own `.venv`, two dependencies) and talks to the **running
Flask app over HTTP**, exactly the way the Angular admin UI or a `curl` script
would.

Reasons:

1. **It exercises the real API surface.** Every tool call goes through the same
   auth, validation, rate-limiting and serialization a human admin hits. If the
   API is wrong, the tool is wrong — no divergent second code path.
2. **Lifecycle independence.** The backend restarts, redeploys, runs in Docker,
   moves to another machine — the MCP server doesn't care, it just needs a URL.
3. **Blast radius.** The MCP server has no database handle. The worst it can do
   is what the admin API allows an authenticated super-admin to do, and every one
   of those actions is already audited by the backend.
4. **Dependency hygiene.** `backend/`'s `requirements.txt` is ~40 packages
   (Flask, SQLAlchemy, Qdrant client, fastembed, Presidio, …). This server needs
   `mcp` and `httpx`. Keeping them separate means neither can break the other's
   install.

`ORANGE_API_BASE` defaults to `http://localhost:5000/api` and is overridable by
environment variable.

---

## 4. Authentication: log in once, cache the JWT, retry once on 401

The admin API uses `flask-jwt-extended` bearer tokens. The server:

1. On the first call that needs auth, POSTs `ORANGE_ADMIN_EMAIL` /
   `ORANGE_ADMIN_PASSWORD` to `/api/auth/login` and caches the returned
   `access_token` in a module-level variable.
2. Attaches `Authorization: Bearer <token>` to every subsequent request.
3. If a request comes back **401**, it assumes the token expired, clears the
   cache, logs in again, and retries the request **once**. If the retry also
   fails — or if `/auth/login` itself fails — that's a real credential problem
   and the error propagates.

This is the smallest thing that survives a long-running agent session without
re-authenticating on every single call.

Credentials come from environment variables, set by AnythingLLM in its config
file (see §9). The dev seed account is `admin@orange.com` / `password123`
(`backend/app/seed.py`).

---

## 5. One request wrapper, and errors returned as *data*

Every HTTP call funnels through a single `_request(method, path, ...)` helper.
Two design choices matter here:

**a) It never raises on a 4xx/5xx.** Instead it returns
`{"error": "...", "status": 404, ...}` — a normal dict. The reason: the *consumer*
is an LLM. If a tool raises, the agent sees an opaque protocol error and usually
gives up. If the tool returns `{"error": "no company named 'Fiatt'"}`, the agent
reads it, realises it misspelled the name, and calls `list_companies` to fix
itself. Errors-as-data turns failures into something the agent can recover from.

**b) The 401-retry lives here**, so all four verbs (GET/POST/PUT/PATCH) get it
for free. A thin `_get()` wraps `_request("GET", ...)` because reads are the
common case.

---

## 6. The agent speaks *names*, the API speaks *IDs*

Admin endpoints take `company_id=5`, `provider_id=3`. An LLM given a user
question about "FIAT" has no idea FIAT is id 5, and asking it to first call a
list endpoint, parse JSON, find the id, then call the real endpoint is three
extra hops it frequently gets wrong.

So every tool accepts **human names** — `company_name="FIAT"`,
`provider_name="Mistral Small"`, `email="user@topnet.com"` — and resolves them
internally with small `_find_company` / `_find_provider` / `_find_user` helpers
(case-insensitive exact match against the list endpoints). If the name doesn't
resolve, the tool returns an error that *names the fix*: "call list_companies()
for valid names".

The agent thinks in the same vocabulary the user does.

---

## 7. Three tiers of tools + MCP annotations

The 18 tools are organised into three tiers, and each carries an MCP
`ToolAnnotations` hint so the agent can reason about how freely to call it.

| Preset | `read_only_hint` | `open_world_hint` | Meaning |
| --- | --- | --- | --- |
| `READ_ONLY` | true | false | Pure read of our own DB. Call anytime. |
| `PROBE` | true | false→**true** | Read-only for us, but reaches out to a third-party LLM. Costs a call. |
| `MUTATING` | false | — | Changes state (but see §8 — a bare call is still only a preview). |

### Tier 1 — Reads (9 tools)

One endpoint each, thin pass-throughs with name→id resolution and a good
docstring: `list_companies`, `list_providers`, `get_usage_summary`,
`get_feedback_summary`, `list_pii_rules`, `list_ingestions`, `list_deletions`,
`qdrant_pool_status`, `list_token_requests`.

The docstrings are written *for the model*: they say when to use the tool, what
the filters mean, and how it relates to other tools ("Disabled providers still
show up here — use `test_provider` to find out if one is actually answering").

### Tier 2 — Diagnostics (3 tools) — where it becomes an agent

These are read-only, but **the tool does multi-step work the agent would
otherwise have to orchestrate itself** (and often botch):

- **`health_check_all_providers`** — lists providers, then loops a live probe
  over each enabled one, timing the round trip, and returns a
  live / degraded / down verdict table plus a one-line summary. This is the real
  "is the platform healthy" answer; `list_providers` only shows configured state.
- **`diagnose_company`** — for one tenant, pulls its caps, last-24h usage,
  all-time usage, feedback score and ingestion history in one call, then applies
  rules ("≥80% of cap used", "satisfaction <60% over ≥5 rated answers",
  "files with blocked chunks", "empty knowledge base") and returns a `flags`
  list plus a `verdict`.
- **`find_problem_providers`** — joins the per-provider feedback breakdown
  against provider config and ranks worst-first, tagging *why* (disabled / low
  score / mediocre score).

Rationale: an LLM told to "check if anything's wrong" *can* call six read tools
and synthesise, but it's slow, it forgets steps, and the synthesis is
inconsistent. Encapsulating the chain in one tool with deterministic thresholds
makes the agent both faster and more reliable, and it makes the demo read like an
operator, not a database browser.

### Tier 3 — Writes (5 tools + `test_provider`)

Real state changes: `set_provider_enabled`, `create_pii_rule`,
`set_company_token_limit`, `set_user_token_limit`, `decide_token_request`.
(`test_provider` sits in this file because it's the one active single-target
probe, but it's a `PROBE`, not a mutation.)

Every mutation is gated — see the next section.

---

## 8. The dry-run / `confirm=true` gate

Every mutating tool has a `confirm: bool = False` parameter. On a bare call
(`confirm` absent or false) the tool does **all its validation and lookups**,
then returns a preview instead of acting:

```json
{
  "dry_run": true,
  "action": "disable provider 'Mistral Small'",
  "would_change": { "enabled": { "from": true, "to": false } },
  "to_apply": "call this tool again with confirm=true"
}
```

Only a second call with `confirm=true` actually issues the PUT/PATCH/POST.

Design points:

- **The check is `confirm is True`, not `if confirm`.** A stray `"true"` string
  or `1` — the kind of thing a model emits under uncertainty — is *not* treated
  as consent.
- **The gate is in the MCP server, not the backend.** A human calling
  `PUT /api/admin/companies/5` still gets no confirmation step; that's correct,
  the admin UI has its own. The gate exists specifically because the caller here
  is a language model acting on a paraphrase of a human request, and a cheap
  "here's what I'm about to do, OK?" round trip removes almost all the risk of it
  acting on a misread.
- **It is a UX safety net, not an authorization boundary.** Anything this server
  can reach, it reaches as full super-admin. `README.md` says so explicitly.
- The shared `_preview()` helper builds the payload so every tool's dry-run looks
  identical and the agent learns the pattern once.

The `platform_admin_briefing` prompt (§9) tells the agent the etiquette: call
once, show the human the preview, re-call with `confirm=true` only after a yes.

---

## 9. Prompt + resources

- **`@mcp.prompt() platform_admin_briefing`** — a short system brief the user can
  select in AnythingLLM: it explains the three tiers, the "work in names" rule,
  and the dry-run etiquette. It means the agent behaves well without the user
  having to write a long system prompt themselves.
- **`@mcp.resource()` `orange://providers` and `orange://companies`** — the live
  provider and company lists exposed as readable resources. AnythingLLM can pull
  these into context directly, so the agent often already knows the tenant/
  provider list without spending a tool call on it.

---

## 10. Wiring into AnythingLLM

AnythingLLM Desktop reads MCP server definitions from:

```
%APPDATA%\anythingllm-desktop\storage\plugins\anythingllm_mcp_servers.json
```

The entry for this server:

```json
{
  "mcpServers": {
    "orange-admin": {
      "command": "C:\\Users\\Amin\\...\\mcp-admin-server\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Amin\\...\\mcp-admin-server\\server.py"],
      "env": {
        "ORANGE_ADMIN_EMAIL": "admin@orange.com",
        "ORANGE_ADMIN_PASSWORD": "password123",
        "ORANGE_API_BASE": "http://localhost:5000/api"
      }
    }
  }
}
```

Notes:

- `command` points at the **venv's** Python so the server's dependencies are on
  the path — not the system Python.
- Paths are absolute and machine-specific. Moving to another PC means editing
  this file (see `../Transfer_and_Setup_Guide.pdf` for the wider transfer plan).
- AnythingLLM **auto-starts** the subprocess when you open the *Agent Skills*
  page or type `@agent` in a chat. It talks JSON-RPC over stdio. There's no port
  and nothing to run manually (`run-server.ps1` exists only for testing the
  server in isolation — it just sits waiting for a stdio client).
- With AnythingLLM's *Generic OpenAI* provider connector, native tool-calling
  isn't guaranteed, so the **`@agent` prefix is required** to route a chat
  through AnythingLLM's own tool-execution loop.

---

## 11. The build, step by step

1. **Scoped it.** Compared AnythingLLM's built-ins against the platform's
   features (§1) and concluded: agent-as-operator, not chat/RAG.
2. **Scaffolded the project.** `mcp-admin-server/` beside `backend/` and
   `frontend/`; fresh `.venv`; `pip install mcp httpx`.
3. **Hit the first gotcha immediately** — see §12: the `mcp` package's server
   class isn't where the tutorials say it is.
4. **Wrote the auth + request core** (`_login`, `_request`, `_get`) and tested it
   against the live backend with a throwaway script before writing any tools.
5. **Built the read tools** one at a time, checking each one's JSON against what
   the endpoint actually returns (field names like `display_name` vs `name`
   matter — the lookup helpers depend on them).
6. **Registered it with AnythingLLM**, opened *Agent Skills*, confirmed the
   server showed up green and the tools were listed.
7. **Drove it from `@agent`** with real questions, watching the tool-call trace.
   Found the model-synthesis flakiness (§12) and the provider-quota issue (§12).
8. **Second pass — made it agentic.** Added the diagnostic tier (encapsulated
   chains), the write tier with the dry-run gate, MCP annotations, the prompt and
   the resources. Reworked the four ad-hoc HTTP helpers into the single
   `_request` wrapper so PUT/PATCH got the 401-retry too.
9. **Verified** — see §13.

---

## 12. Gotchas and lessons

- **`FastMCP` was renamed.** In the installed `mcp` package (v2.0.0) the server
  class is `from mcp.server import MCPServer`, not the `FastMCP` that every
  tutorial and the older docs reference. The decorator API
  (`@mcp.tool()`, `@mcp.prompt()`, `@mcp.resource()`) is otherwise the same.
- **`ToolAnnotations` lives in `mcp.types`** and its fields are snake_case
  (`read_only_hint`, `destructive_hint`, `idempotent_hint`, `open_world_hint`).
- **AnythingLLM was already running natively** on port 3001. Nearly stood up a
  second copy in Docker before noticing — reverted that.
- **Provider quota burns faster through AnythingLLM.** When AnythingLLM is the
  chat model (not just the agent host) it calls the upstream LLM directly,
  bypassing this platform's own `llm_router.py` rate-limiter and fallback. GPT-OSS
  / Cerebras runs out fast this way. Groq's `llama-3.3-70b-versatile` held up
  best in practice; local Ollama is the only truly unlimited option.
- **A successful tool call can still produce a bad answer.** The model sometimes
  echoes the raw tool-result JSON instead of writing a sentence — a synthesis
  failure, not a server bug. Retrying, or switching to a stronger agent model,
  fixes it.
- **Generic OpenAI connector has no model dropdown** (plain text field, by
  design — it can't enumerate an arbitrary endpoint's models) and no guaranteed
  native tool-calling, hence the `@agent` requirement.
- **Errors must be data, not exceptions** (§5) — this was the single biggest
  improvement to how well the agent recovered from its own mistakes.

---

## 13. Testing and verification

There is no unit-test suite for this server (it's a thin bridge; the logic worth
testing is in `backend/`). Verification was done by driving the real tools
against the live backend:

- **Registration** — all 18 tools, 1 prompt and 2 resources appear via the MCP
  `list_tools` / `list_prompts` / `list_resources` calls, with the expected
  annotations.
- **Every read** — returns the shape the code expects; name→id resolution works;
  unknown names return the guiding error.
- **Every diagnostic** — run end to end against real data
  (`health_check_all_providers` correctly reported "5 live, 6 down" on the dev
  seed; the "down" ones are seed providers without working keys, which is itself
  a good demo of the tool doing its job).
- **Every write** — dry-run path returns a preview and touches nothing; bad
  input (invalid regex, unknown email, non-existent request id) returns a clean
  error; the `confirm=true` path was tested by setting a company's token cap and
  then restoring it, confirming the change landed and reverted.
- **Boot** — `python server.py` starts the stdio loop and exits cleanly on EOF;
  `py_compile` is clean.

To repeat the manual check:

```powershell
cd mcp-admin-server
$env:ORANGE_ADMIN_EMAIL = "admin@orange.com"
$env:ORANGE_ADMIN_PASSWORD = "password123"
./.venv/Scripts/python.exe server.py   # then Ctrl+C — it waits silently for a client
```

or drive individual tool functions by importing `server.py` as a module.

---

## 14. Adding a new tool

1. Find or add the admin endpoint in `backend/app/blueprints/`.
2. Write a function in `server.py`, decorated with `@mcp.tool(annotations=...)`.
   Pick `READ_ONLY`, `PROBE` or `MUTATING`.
3. Take **names**, not ids, as arguments; resolve with the `_find_*` helpers.
4. Call the endpoint through `_request(...)` / `_get(...)`.
5. If it mutates: add `confirm: bool = False`, do all validation first, then
   `dry = _preview(confirm, "<action>", {<changes>})` and `if dry: return dry`
   before the real call.
6. Write the docstring **for the model** — when to use it, what the args mean,
   which tool to reach for next.
7. Restart AnythingLLM's agent (reopen *Agent Skills*) to pick up the change.

---

## 15. Limitations and security posture

- **Full super-admin rights.** The server holds one admin credential and every
  tool acts with it. There is no per-tool permission scoping.
- **`confirm=true` is not authorization.** It's a misread-guard for an LLM
  caller, nothing more.
- **Credentials in plaintext.** `anythingllm_mcp_servers.json` stores the admin
  password in clear text, local to the machine, outside this repo. Same exposure
  as the seed script. If ever pointed at a real production admin account, that
  file must be protected accordingly.
- **No audit log of its own.** It relies entirely on the backend auditing the
  actions it triggers (ingestions, deletions, provider changes are logged there;
  token-cap changes are not, currently).
- **Single-user assumption.** JWT caching in a module global is fine for one
  agent session; it is not built for concurrent multi-tenant use.

---

## 16. File map

```
mcp-admin-server/
├── server.py            the MCP server — all 18 tools, prompt, resources
├── requirements.txt     mcp>=1.2.0, httpx>=0.27.0
├── README.md            quick reference: tool list, how to run, how it's registered
├── HOW_IT_WAS_BUILT.md  this document
├── run-server.ps1       manual launch for testing in isolation
└── .venv/               isolated environment (mcp 2.0.0, httpx 0.28.1)
```

Registered externally at
`%APPDATA%\anythingllm-desktop\storage\plugins\anythingllm_mcp_servers.json`.
