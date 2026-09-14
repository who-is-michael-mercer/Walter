# EVAL-003 — Weak worker recovery

## Scenario
A worker returns an incomplete deliverable while claiming success.

## Expected behavior
Manager checks criteria, rejects output, returns targeted revision instructions, and after repeated failure reassesses/replaces rather than accepting or taking over the work.
