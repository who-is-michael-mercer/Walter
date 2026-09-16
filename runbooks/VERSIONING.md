# Versioning

Use semantic versioning for Walter behavior:

- PATCH: clarification without intended behavior change.
- MINOR: compatible capability, protocol, command, template, or state-schema addition.
- MAJOR: incompatible authority, lifecycle, persistence, task-packet, or runtime contract change.

For each release record the system-prompt, permissions, capabilities, schema/migration, CLI, sandbox, approval, and known-limit changes plus test/eval evidence.

Operational snapshots carry a schema version. Schema v2 transactionally migrates supported v1 snapshots and retains exact pre-migration rows in `schema_migration_backups`; unresolved approval identity/scope becomes an explicit blocked recovery gate. Unsupported or inconsistent versions are rejected rather than guessed. Conversation-session compatibility is separate.

Candidate Walter changes remain on isolated candidate branches. Release evidence follows the authority chain: trusted validation, independent review, Manager acceptance, then a human approval bound to the exact candidate and target. Approval does not merge or push. Behavioral changes need relevant deterministic tests and judgment evals before promotion.
