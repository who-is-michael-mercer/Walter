# Quality Assurance Protocol

## Core rule

No worker output is complete merely because the worker says it is.

## Manager acceptance check

For every task, the Manager checks:

- required deliverable exists;
- requested scope is satisfied;
- explicit acceptance criteria are met;
- obvious contradictions or omissions are absent;
- evidence/verification appropriate to the domain is present.

This check is managerial acceptance, not a substitute for specialist QA.

## Independent reviewer threshold

Create an independent reviewer when one or more apply:

- high impact;
- specialist knowledge beyond routine Manager inspection;
- difficult-to-verify correctness;
- security, safety, compliance, or legal relevance;
- irreversible consequences;
- externally visible or reputation-sensitive output;
- low confidence;
- conflicting worker results;
- historically weak worker performance.

## Domain-appropriate evidence

- Research: credible sources, traceable evidence, freshness as needed.
- Code/technical work: tests, builds, static checks, observable runtime behavior, or equivalent verification.
- Data work: reproducibility, integrity checks, reconciliations.
- Creative work: brief adherence, constraints, consistency, and relevant reviewer judgment.
- Strategy: evidence, internal coherence, assumptions, risks, and explicit tradeoffs.

## Revisions

Default maximum: 2 failed revision cycles for the same worker before reassessment.

After repeated failure, the Manager should determine whether the cause is:

- poor worker fit;
- bad task definition;
- missing input;
- unrealistic acceptance criteria;
- hidden dependency;
- tool/access limitation.

Then replace, split, revise, or replan rather than looping.

## Conflicting outputs

Do not average conflicting specialist conclusions. Compare evidence. If material disagreement remains, create an adjudicator or targeted follow-up specialist.
