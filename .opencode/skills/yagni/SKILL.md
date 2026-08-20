---
name: yagni
description: Apply aggressive but safe YAGNI and minimal-diff principles during planning, implementation, and review.
---

# YAGNI

Implement only what is required by the current specification and acceptance criteria.

Prefer:

1. no implementation when existing behavior already satisfies the requirement
2. existing project code/patterns
3. standard library
4. native framework/platform behavior
5. existing dependencies
6. a small direct implementation
7. a new abstraction/dependency only when necessary

Flag or remove:

- speculative extensibility
- abstractions with one implementation
- configuration without a current use
- generic frameworks for one use case
- wrappers that merely rename existing APIs
- premature plugin/factory/base-class systems
- dependencies for trivial functionality
- unrelated cleanup
- future requirements not requested

A smaller diff is preferred only when it remains fully correct.

Never trade away:

- correctness
- security
- trust-boundary validation
- data integrity
- accessibility
- explicit acceptance criteria
