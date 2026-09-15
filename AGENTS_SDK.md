# Walter on the OpenAI Agents SDK

This branch contains Walter's first executable runtime adapter.

The operating doctrine remains in the repository's existing Markdown contracts. The runtime
loads `SYSTEM_PROMPT.md`, exposes a typed `delegate_task` tool to Walter, and creates temporary
specialist agents on demand. Workers receive only their explicit task packet and return a
Pydantic-validated `WorkerResult`.

## 1. Switch to the runtime branch

```bash
git fetch origin
git switch runtime/agents-sdk
git pull --ff-only
```

## 2. Create and activate a virtual environment

Run these as separate commands:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 3. Install Walter

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

The editable install is intentional: this runtime reads Walter's canonical `SYSTEM_PROMPT.md`
directly from the repository checkout.

## 4. Configure the API key

If `OPENAI_API_KEY` is already exported in your shell, nothing else is required.

Alternatively create a local `.env` file in the repository root:

```text
OPENAI_API_KEY=your_key_here
```

`.env` is gitignored. Never commit the key.

Optional model overrides:

```text
WALTER_MODEL=your_manager_model
WALTER_WORKER_MODEL=your_worker_model
```

If those variables are omitted, the Agents SDK's configured/default OpenAI model is used.

## 5. Start Walter

Interactive mode:

```bash
walter
```

Useful interactive commands:

```text
:clear   clear the current Walter conversation
:quit    exit Walter
```

The default interactive session is persisted locally in `.local/walter-sessions.db`.

Use a separate named conversation when desired:

```bash
walter --session brand-project
```

One-shot mode:

```bash
walter "Create a launch strategy for a new electrolyte brand aimed at multi-day music festivals."
```

A one-shot run is stateless unless you explicitly add `--session NAME`.

## Capability routing

Walter now chooses between two least-privilege worker capability profiles:

- `model_only` — reasoning, writing, synthesis, critique, planning, and other tasks that do not
  require fresh external evidence.
- `web_search` — adds the Agents SDK hosted `WebSearchTool` for research tasks that materially
  depend on current or externally verifiable public information.

Walter still owns the decision to grant web search. A worker does not choose or expand its own
capabilities. Web-enabled workers must return the sources they actually relied on in their
structured `WorkerResult`.

Workers still do not have shell, filesystem, GitHub, email, or other action tools. Those remain
future capability profiles.

## Tracing and proving delegation

Every goal is wrapped in a named `Walter orchestration` trace. After each completed goal, the
CLI prints a trace ID such as:

```text
Trace ID: trace_...
```

Use that ID in the OpenAI Dashboard Trace viewer. The trace hierarchy should show Walter's
model turns, the `delegate_task` function calls, and nested specialist agent/model/tool spans.
A web-enabled researcher will additionally show a hosted web-search tool call.

Trace content is redacted by default: structure and spans are exported without model/tool
inputs and outputs. For a controlled debugging session where you intentionally want those
payloads visible in the trace, start Walter with:

```bash
walter --trace-sensitive
```

Do not use `--trace-sensitive` for goals containing secrets or information you do not want in
trace payloads.

## Recommended verification test

Start a fresh named session:

```bash
walter --session web-test
```

Then give Walter this goal:

```text
Research the current OpenAI Agents SDK Python capabilities for web search and tracing. Use fresh external sources where appropriate. Have a separate reviewer assess whether the research is adequately sourced and current, then give me a concise recommendation for how Walter should use those capabilities.
```

Expected behavior:

1. Walter defines acceptance criteria before delegation.
2. The research lane receives `tool_policy=web_search`.
3. The researcher performs real hosted web search and returns source URLs.
4. A review lane is separately delegated; it should normally remain `model_only` when the
   accepted research packet contains enough evidence to review.
5. Walter accepts, revises, or replaces work before giving the final recommendation.
6. The terminal prints one trace ID for the whole orchestration workflow.

## Runtime files

```text
pyproject.toml
src/walter/__init__.py
src/walter/contracts.py
src/walter/runtime.py
src/walter/cli.py
AGENTS_SDK.md
```

`contracts.py` defines Pydantic task/result contracts and capability policies. `runtime.py`
implements dynamic specialist creation, least-privilege tool routing, and delegation. `cli.py`
provides the `walter` command, local sessions, trace privacy configuration, and trace IDs.
