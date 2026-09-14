# Versioning

Use semantic versioning for Manager behavior.

- PATCH: wording or clarification with no intended behavioral change.
- MINOR: new capability, protocol, template, or non-breaking behavior change.
- MAJOR: changes to core authority, delegation model, task-state semantics, or compatibility with existing task packets.

For each release record:

- system prompt changes;
- permission changes;
- tool policy changes;
- state/schema changes;
- eval results;
- known issues.

Behavioral changes should not be merged without relevant eval coverage.
