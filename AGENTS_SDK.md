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
git pull
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

The editable install is intentional: this first runtime reads Walter's canonical
`SYSTEM_PROMPT.md` directly from the repository checkout.

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

Then give Walter a goal at the prompt:

```text
walter> Develop three distinct positioning directions for a new premium camping brand and recommend the strongest one.
```

Walter will decide what specialist lanes are required, create temporary workers through the
Agents SDK, inspect their structured outputs, and return the final outcome.

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

## Current v0 capability boundary

This first runtime proves Walter's Manager/subagent loop. Specialist workers currently have
model reasoning plus structured output only. They do not yet receive web, shell, filesystem,
GitHub, email, or other external action tools.

That limitation is deliberate. It lets the core orchestration behavior run before adding tool
routing and permissions. Walter is instructed to report a blocker rather than pretend an
external action or verification occurred.

The next runtime layer should add least-privilege capability profiles so Walter can create, for
example, a research worker with web search or an implementation worker with a sandboxed
workspace without granting those tools to every agent.

## Files added by this runtime

```text
pyproject.toml
src/walter/__init__.py
src/walter/contracts.py
src/walter/runtime.py
src/walter/cli.py
AGENTS_SDK.md
```

`contracts.py` defines the Pydantic task/result contracts. `runtime.py` implements dynamic
specialist creation and delegation. `cli.py` provides the `walter` terminal command and local
session persistence.
