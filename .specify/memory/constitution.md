<!--
Sync Impact Report
Version change: unversioned template -> 1.0.0
Modified principles:
- Template principle 1 -> I. Incremental Evolution, Not Rewrite
- Template principle 2 -> II. Runtime First, UI Second
- Template principle 3 -> III. Replaceable Speech and Capability Interfaces
- Template principle 4 -> IV. Safety and Accessibility Are Product Requirements
- Template principle 5 -> V. Tests, Observability, and Latency Are Mandatory
Added sections:
- Architecture Guardrails
- Delivery Workflow & Quality Gates
Removed sections:
- None
Templates requiring updates:
- Updated: .specify/templates/plan-template.md
- Updated: .specify/templates/spec-template.md
- Updated: .specify/templates/tasks-template.md
- Not present: .specify/templates/commands/*.md
Follow-up TODOs:
- None
-->
# Voice Assistant Constitution

## Core Principles

### I. Incremental Evolution, Not Rewrite
All changes MUST preserve the existing layered application (`main.py`, `core/`,
`settings/`, `tts/`, and `ui/`) unless a documented migration plan defines the
target state, rollback path, and validation steps. Work MUST ship in small,
reversible slices; sweeping rewrites that replace multiple layers at once are
prohibited without explicit approval.

Rationale: The project already contains working behavior, and the target
product is safety-critical enough that regression-controlled evolution is safer
than restart-driven design.

### II. Runtime First, UI Second
Production voice runtime logic MUST live in runtime or service layers that can
be executed without the GUI. Files under `ui/` MAY host debug, demo, and
visualization behavior, but MUST NOT become the authoritative home for core
runtime workflows. `main.py` MUST stay thin orchestration only, and
`settings/settings_manager.py` MUST stay focused on runtime configuration
rather than feature-specific business rules.

Rationale: The final target is a headless smart-glasses assistant; the GUI is
valuable for debugging, not as the primary runtime architecture.

### III. Replaceable Speech and Capability Interfaces
Wake detection, STT, TTS, and hardware or vision capabilities MUST be
introduced behind explicit adapters or service interfaces. No change MAY
hard-wire the assistant to a single provider when an abstraction boundary is
available. Any provider that depends on network access MUST define timeout
behavior, failure handling, and a fallback or degradation path before it can be
treated as production-ready. Capability handlers MUST return a structured result
contract containing `spoken_text`, `status`, `payload`, and `error_code` when
applicable.

Rationale: The assistant must tolerate provider changes, offline conditions,
and future device integrations without destabilizing the rest of the stack.

### IV. Safety and Accessibility Are Product Requirements
Voice interactions MUST optimize for blind and low-vision use: responses must
be brief, unambiguous, and task-oriented, and non-visual operation must remain
possible for every primary flow. Commands with shutdown, close, or otherwise
risky behavior MUST be explicitly safeguarded and MUST NOT silently terminate
the primary assistant loop. Specs and plans for new features MUST document
noisy-environment behavior, weak-network behavior, and any non-verbal feedback
needs when relevant.

Rationale: A confusing answer or unsafe state transition is more costly in an
assistive wearable than in a general consumer app.

### V. Tests, Observability, and Latency Are Mandatory
Changes to parsing, resolving, dispatching, runtime orchestration, settings
application, or provider integration MUST include automated tests and a
repeatable smoke validation path. Runtime-affecting work MUST emit structured
logs for startup, listening, wake events, dispatch, provider failures, and
capability execution. Plans MUST state measurable latency or reliability
targets, or establish baselines, for wake, STT, TTS, command execution, and
recovery from failure.

Rationale: The plan explicitly calls out missing quality gates; reliability
cannot improve if behavior is not tested, logged, and measured.

## Architecture Guardrails

- No full rewrite is allowed while the project is still extracting value from
  the current codebase.
- `ui/gui_app.py` and related UI files remain a debug and demo surface;
  headless execution is the reference path for the final wearable runtime.
- `core/parser.py` MUST be protected by tests before major behavior changes,
  and command understanding improvements SHOULD be incremental rather than
  replacement-driven.
- `core/dispatcher.py` and `core/resolver.py` MAY evolve, but they MUST
  preserve clear command routing and move toward structured commands and
  structured results.
- `controllers/mock_controllers.py` MAY remain as a transition layer, but real
  capabilities MUST graduate into dedicated modules or services rather than
  expanding the mock file indefinitely.
- `settings/settings_manager.py` remains the central runtime settings authority
  and MUST NOT accumulate unrelated business workflows.

## Delivery Workflow & Quality Gates

- Every feature spec MUST identify the user-facing task, affected runtime
  layer, accessibility impact, degraded-mode behavior, and success metrics.
- Every implementation plan MUST complete the Constitution Check before design
  begins and re-check it after design changes.
- Every task list MUST include the validation work needed for tests,
  observability, and runtime verification when a change touches protected areas
  named in Principle V.
- Each phase of work MUST end with a real execution check, such as console
  mode, headless runtime validation, or a documented smoke test in the GUI
  debug path.
- New integrations with speech providers, sensors, or vision modules MUST
  define interface contracts, error handling, and fallback expectations before
  implementation is considered complete.

## Governance

This constitution supersedes conflicting local planning habits and applies to
specifications, implementation plans, task lists, and code reviews for this
repository. Compliance MUST be checked during planning and again during
implementation review, and any intentional deviation MUST be documented in the
plan's Complexity Tracking section with a concrete justification and a simpler
rejected alternative.

Amendments MUST update this file and any affected templates in the same change.
Versioning follows semantic rules for governance: MAJOR for incompatible
principle removals or redefinitions, MINOR for new principles or materially
expanded requirements, and PATCH for clarifications that do not change
expectations. Reviews MUST reject work that does not satisfy the constitution
or document an approved exception.

**Version**: 1.0.0 | **Ratified**: 2026-04-16 | **Last Amended**: 2026-04-16
