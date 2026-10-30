<!--
Sync Impact Report
Version change: (template, unratified) → 1.0.0
Modified principles: n/a (initial ratification; template placeholders replaced)
Pre-commit review edits (still 1.0.0, never committed before):
  - II, III: restated AGENTS.md rules replaced by section references; III keeps only FR-traceability
  - V: "Stop on Ambiguity" → "Ambiguity by Stage" (marker/assumption in specify/clarify/plan,
    stop and ask in tasks/implement)
  - Governance: references to non-existent CONSTITUTION_VERSION/LAST_AMENDED_DATE fixed;
    requirement to delete this report before commit removed
Added sections:
  - Core Principles: Source of Truth Precedence, Layered Architecture, Feature Test Traceability,
    Spec-Driven Scope, Ambiguity by Stage
  - Spec Kit Feature Organization (SECTION_2)
  - Preserved OpenSpec Behavior (SECTION_3)
  - Governance
Removed sections: none (first filled version)
Deferred TODOs: none
-->

# Review Desk Constitution

## Core Principles

### I. Source of Truth Precedence
This constitution does not restate project rules; it points to where they live. The binding
sources are `AGENTS.md` (agent workflow, architecture layers, test naming, prohibitions) and
`docs/baseline.md` (frozen MVP behavior). Where this constitution and either of those documents
disagree, `AGENTS.md` and `docs/baseline.md` win and this document MUST be corrected to match.
Rationale: a single project already has two authoritative, actively maintained documents for
rules and behavior; the constitution exists to add what they do not cover, not to fork them.

### II. Layered Architecture
See `AGENTS.md`, section «Архитектура», and `docs/architecture.md`. Spec Kit plans and tasks
follow them as written.

### III. Feature Test Traceability
Check gate, test-first and test naming: see `AGENTS.md`, sections «Проверка» and «Процесс».
Added for Spec Kit: each test of a Spec Kit feature MUST reference, in its name or docstring, the
`FR-NNN` requirement from that feature's own `specs/NNN-<name>/spec.md`.

### IV. Spec-Driven Scope
A feature MUST be implemented only to the extent described by its accepted specification —
either an OpenSpec change (`openspec/changes/<name>/`, later `openspec/specs/`) or a Spec Kit
feature (`specs/NNN-<name>/`) — and MUST NOT change behavior frozen in `docs/baseline.md` unless
the spec explicitly says so. Scope not written in the accepted spec is not in scope for the
change. Rationale: prevents silent architecture or behavior drift outside of what was reviewed
and accepted.

### V. Ambiguity by Stage
During `specify`, `clarify` and `plan`, an ambiguity or a conflict with `docs/architecture.md`
is recorded in the artifact as a `[NEEDS CLARIFICATION: ...]` marker or as an explicitly stated
assumption, and work continues. During `tasks` and `implement`, the agent stops and asks
(`AGENTS.md`, section «Процесс»).

## Spec Kit Feature Organization

Spec Kit features live under `specs/NNN-<name>/` (numbered, kebab-case name), mirroring how
OpenSpec features live under `openspec/changes/<name>/` and `openspec/specs/<name>/`.

The contract shared across all Spec Kit features (e.g. shapes, events, or data that more than one
feature depends on) lives in `specs/line-comments-contract.md`. When a feature's own spec
conflicts with this contract, the contract wins and the feature spec MUST be corrected. A feature
spec MAY extend the contract with details specific to that feature, but MUST NOT redefine what the
contract already defines.

## Preserved OpenSpec Behavior

Behavior already captured in `openspec/specs/` — currently `review-queue` and `path-id-bounds` —
remains in force exactly as specified there. A Spec Kit feature MUST NOT regress it; where a new
feature touches the same area, the relevant `openspec/specs/` entry is read the same way
`docs/baseline.md` is read: as a constraint to preserve, not a default to renegotiate. If a Spec
Kit feature needs to change that behavior, this is a conflict handled per Principle V, not
something to resolve by editing `openspec/specs/` from a Spec Kit workflow.

## Governance

This constitution is subordinate to `AGENTS.md` and `docs/baseline.md` (Principle I); amendments
here MUST NOT contradict either without first amending those documents through their own, separate
process. Amendments to this constitution are made by editing
`.specify/memory/constitution.md` directly, incrementing **Version** in the footer of this file
per semantic versioning (MAJOR: backward-incompatible principle removal/redefinition; MINOR: new
principle or materially expanded guidance; PATCH: wording/clarification only), and updating
**Last Amended** there. Every amendment updates the Sync Impact Report comment at the top of the
file describing what changed. Compliance is checked the same way all other work
is checked: `sh scripts/check.sh` must print `CHECK: PASS`, and any new or changed behavior is
traceable to an accepted spec (Principle IV). For day-to-day workflow rules not covered here, see
`AGENTS.md`.

**Version**: 1.0.0 | **Ratified**: 2026-10-30 | **Last Amended**: 2026-10-30
