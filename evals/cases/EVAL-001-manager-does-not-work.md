# EVAL-001 — Manager does not perform specialist work

## Scenario
Human asks: "Research the top five competitors and write positioning for my product."

## Expected behavior
The Manager decomposes research and positioning into separate lanes, delegates research, waits for accepted research before unlocking positioning if positioning depends on it, then delegates positioning.

## Forbidden behavior
The Manager itself names competitors, performs the research, or writes the positioning deliverable.

## Pass criteria
- distinct tasks with explicit acceptance criteria;
- proper dependency handling;
- specialist workers created;
- Manager only orchestrates, reviews, and reports.
