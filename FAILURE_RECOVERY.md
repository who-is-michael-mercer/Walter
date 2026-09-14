# Failure Recovery

## Failure classes

Classify before acting:

1. Worker execution failure.
2. Poor task decomposition.
3. Missing or invalid input.
4. Tool/runtime failure.
5. Dependency failure.
6. Permission/access failure.
7. Ambiguous goal or constraint.
8. Quality/acceptance failure.
9. Genuine external blocker.

## Recovery sequence

1. Capture the actual failure and current state.
2. Identify the failure class.
3. Preserve valid completed work.
4. Choose the smallest corrective action.
5. Update task packet or graph if needed.
6. Retry only if the method is now materially different or the failure was transient.
7. Replace the worker when worker fit is the problem.
8. Escalate only when the interruption policy is met.

## Prohibited behavior

- blind identical retries;
- pretending partial work is complete;
- Manager emergency takeover of specialist work;
- hiding blockers;
- throwing away valid artifacts unnecessarily.

## Partial completion

When full completion is impossible, maximize useful completed work, preserve artifacts, identify the exact blocker, and report the remaining path to completion.
