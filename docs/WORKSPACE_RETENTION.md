# Workspace retention and environment recovery

Normal startup uses `.local/sandboxes`. Readiness runs retain independent registries
under `.local/readiness/<unique-id>`; normal startup never searches them or falls
back to them. The durable operations database remains `.local/walter-operations.db`.

An authenticated active grant binds its original dependency environment. A mismatch
reports the registry, bound environment, and current environment and stops startup
before creating a durable run. Restore the original environment and use the original
registry to resume that run. Never edit, reset, skip, or rebind retained grants.

To start independent work with the current environment, explicitly choose an unused,
repository-contained directory:

```sh
walter --workspace-state-root .local/sandboxes-new "New objective"
walter run resume RUN_ID --workspace-state-root .local/sandboxes-new
```

Use the same registry for subsequent resumes, including `resume --execute`. A fresh
registry does not recover candidates belonging to another registry. Record the chosen
path with the run's operational notes. Symlinked or out-of-repository registry roots
are rejected; authentication and grant checks still apply to existing registries.

Retention is based on lifecycle and review, with no age expiry or automatic deletion.
Retain all active candidates, submitted or review-required candidates and reviewer
grants, and accepted candidates awaiting approval or promotion. Keep associated
manifests, keys, worktrees, branches, artifacts, events, and approval evidence together.
Closed grant metadata and historical evidence remain retained until explicit reviewed
cleanup. Starting or resuming another run does not authorize cleanup.

Before any explicit cleanup, review the durable run, task, artifact, review, and
approval records; establish that no active work, outstanding review, pending approval,
or other retained reference requires the candidate evidence. Preserve the agreed audit
record and obtain explicit authorization for deletion. A stale dependency environment
alone is never grounds for cleanup.

This is an operator policy, not an automatic cleanup enforcement mechanism. The
existing low-level `WorkspaceManager.cleanup` is destructive and trusts its caller;
it does not inspect durable review or approval state. No retention sweeper or general
cleanup command is provided by this change.
