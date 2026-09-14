# Delegation Protocol

1. Confirm task state is `READY`.
2. Confirm accepted prerequisites exist.
3. Define/update acceptance criteria.
4. Select the narrow specialist lane.
5. Create an agent ID and task packet.
6. Grant minimum sufficient context and tools.
7. Mark task `ACTIVE`.
8. Receive structured result.
9. Mark task `REVIEW`.
10. Perform Manager acceptance check.
11. Invoke independent reviewer if threshold is met.
12. Accept -> `COMPLETE`; reject -> `REVISION`; inability to proceed -> classify failure.
13. Promote accepted artifact to canonical state.
14. Unlock newly satisfied dependent tasks.
15. Retire worker unless lane continuity is justified.
