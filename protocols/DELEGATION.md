# Delegation Protocol

1. Confirm task state is `READY`.
2. Confirm every dependency is `ACCEPTED` and required input/capability exists.
3. Confirm acceptance criteria, trusted checks, review policy, and bounds were declared.
4. Select one narrow specialist lane and capability profile.
5. Create an assignment ID and minimum-sufficient task packet.
6. Bind any workspace and grant only profile-derived tools.
7. Record the assignment ID with `DELEGATED`, then `RUNNING` when execution begins.
8. Accept a structured provisional result only when task, assignment ID, and worker match current state; create a versioned candidate artifact (`SUBMITTED`).
9. Run every trusted validation and commission a distinct reviewer when required (`REVIEWING`).
10. Perform the Manager acceptance check against the exact artifact identity.
11. Pass -> `ACCEPTED`; correction -> `REVISION_REQUIRED`; reassessment -> `REPLACED`; execution problem -> classify and record `FAILED` or `BLOCKED` as appropriate.
12. Promote only the accepted artifact into canonical run state.
13. Recalculate readiness; only `ACCEPTED` dependencies unlock downstream work.
14. Retire the worker unless bounded continuation in the same lane is justified.

All transitions are requested through the durable kernel. Worker completion status never advances task state by itself.

If worker status is `blocked` or `needs_revision`, persist its partial result without creating an artifact. Classify and recover it explicitly; do not report `TOOL_FAILURE` unless tool execution actually threw. A structured capability request must carry requested capability, reason, and risk and enters the separate approval lifecycle.

For `repo_reader` or `developer_sandbox` escalation, bind the exact Manager-created workspace into human approval. Atomic/idempotent application must complete before redelegation. Reuse the approved workspace read-only for the reader profile or with bounded writes/checks for the developer profile. Developer delegation is invalid unless `compile` or `pytest` was declared at plan, replan, or change time.
