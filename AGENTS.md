# BrewFlow — Agent Instructions

## Purpose

Read `docs/product.md` before making product assumptions.
Read `docs/architecture.md` before making architectural changes.

If either document is incomplete, infer only what is safe from the existing repository.
Do not manufacture requirements.

## Commands

Replace these placeholders as soon as the project stack is chosen.

```text
Install:    <PROJECT_INSTALL_COMMAND>
Test:       <PROJECT_TEST_COMMAND>
Lint:       <PROJECT_LINT_COMMAND>
Typecheck:  <PROJECT_TYPECHECK_COMMAND>
Build:      <PROJECT_BUILD_COMMAND>
```

Prefer focused checks while iterating, then run the project's required full checks before
reporting completion.

## Implementation philosophy

Apply YAGNI.

Prefer, in order:

1. Existing behavior that already satisfies the requirement.
2. Existing project code and patterns.
3. Standard-library functionality.
4. Native framework/platform functionality.
5. Existing dependencies.
6. A small direct implementation.
7. New abstractions/dependencies only when the above are insufficient.

Do not introduce:

- speculative extensibility
- abstractions with one implementation
- configuration without a current requirement
- generic frameworks for a single use case
- wrappers that merely rename an existing API
- unnecessary factories or base classes
- premature plugin systems
- unnecessary dependency injection
- dependencies for trivial functionality
- unrelated refactors

Do not implement anticipated future requirements.

Minimalism must never compromise correctness, security, trust-boundary validation,
data integrity, accessibility, or explicit acceptance criteria.

## Scope

Work only in the current repository/worktree.

Never without explicit user approval:

- use `sudo`
- invoke Docker
- install system packages
- modify system configuration
- access files outside the repository
- perform destructive or irreversible data operations
- push to remote branches
- alter production infrastructure

Never execute destructive recursive operations against `/`, `~`, `..`, `/home`,
`/mnt`, `/usr`, `/etc`, or `/var`.

## Git

- Keep changes scoped to the request.
- Do not modify unrelated files.
- Inspect the diff before reporting completion.
- Do not commit or push unless explicitly requested.
- For competing implementations, use separate Git worktrees.

## Planning

For non-trivial work, identify:

- current behavior
- minimum required change
- affected components
- tests/validation
- risks
- assumptions that materially affect implementation
- things deliberately not being built because of YAGNI

Do not implement during a planning-only request.

## Communication

Be concise.

Do not narrate routine actions.
Do not repeat the task specification.
Do not reproduce code already written to files unless asked.

When reporting completion, provide only:

1. What changed.
2. Tests/checks run.
3. Any unresolved issue or deliberate trade-off.

If there is no unresolved issue, do not invent one.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
