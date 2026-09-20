# Reporting Protocol

## Milestone update

Report only when materially useful:

- completed gate;
- major accepted deliverable;
- changed plan/assumption;
- significant risk;
- approval requirement;
- genuine blocker.

## Final report

Include:

- Run status: `completed`, `active`, or the exact persisted status
- Completed deliverables
- Key decisions
- Verification / QA performed
- Unresolved items
- Artifact references

Do not return a transcript of worker activity unless explicitly requested.

Use the canonical task states defined in OPERATING_MODEL.md when discussing tasks. A worker-result status such as `completed` is provisional
and must not be reported as task or run acceptance.

Report capability requests by ID, requested profile, reason/risk, linked approval, and current `pending`/`approved`/`denied`/`escalated` status. Make clear that `approved` is not yet applied authority and provisional worker output is not an artifact.
For repository profiles also report the exact workspace ID, whether a rejected workspace was cleaned, and whether atomic application has durably reached `escalated`; retries after restart should report the same applied identity.
