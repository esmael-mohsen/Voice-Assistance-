# Research: Command Layer Hardening

## Decision: Preserve the current command set and formalize it as categorized metadata

- **Decision**: Keep the existing supported commands as the full scope for this
  phase, but represent them with explicit metadata for category, validation
  profile, routing target, and follow-up behavior instead of a bare
  `COMMAND_KEYWORDS` dictionary alone.
- **Rationale**: The spec explicitly limits scope to hardening the current
  command set. Adding metadata allows better validation and routing without
  expanding capability surface area.
- **Alternatives considered**:
  - Add new commands while refactoring: rejected because it mixes trust work
    with scope growth and weakens regression confidence.
  - Keep a plain keyword-only mapping: rejected because it cannot express
    system-command safeguards, clarification requirements, or follow-up rules.

## Decision: Replace one global threshold with risk-based validation profiles

- **Decision**: Keep fuzzy matching with `rapidfuzz`, but move from one global
  threshold to intent-specific validation profiles grouped by risk:
  capability, settings, lower-risk system, and high-consequence system.
- **Rationale**: The current single threshold makes risky commands too easy to
  misfire and low-risk commands too hard to tune independently. Risk-based
  thresholds align with the clarified safety rules.
- **Alternatives considered**:
  - Exact-match only: rejected because bilingual speech recognition noise would
    cause too many false negatives.
  - One stricter global threshold for every command: rejected because it would
    hurt everyday command usability without fully solving protected-command
    safety.

## Decision: Parse into structured intent data before resolver logic runs

- **Decision**: Make the parser return a structured intent candidate with
  intent identity, category, matched phrase, confidence, validation outcome,
  and reason codes instead of only `CommandMatch`.
- **Rationale**: Structured parse results allow the dispatcher and resolver to
  separate "matched", "weak match", "ambiguous", and "rejected" cases without
  reparsing text or inferring meaning from logs.
- **Alternatives considered**:
  - Keep the current `CommandMatch` and add ad hoc flags elsewhere: rejected
    because decision details would remain fragmented.
  - Push all validation into the resolver: rejected because routing depends on
    category and safety classification that should exist before execution.

## Decision: Centralize parameter extraction and one-shot follow-up context in the resolver

- **Decision**: Keep execution routing in `core.resolver`, but replace the
  loose `SESSION_STATE` dictionary with a structured session context that can
  store one immediate follow-up dependency, pending clarification, and pending
  confirmation state.
- **Rationale**: The resolver already owns parameter inference and command-to-
  controller mapping. Extending that responsibility with a small structured
  context keeps follow-up handling localized and testable.
- **Alternatives considered**:
  - Store follow-up state in `core.assistant_runtime`: rejected because runtime
    should not become the command-semantic authority.
  - Keep a raw mutable dictionary: rejected because it is too implicit for safe
    clarification and confirmation flows.

## Decision: Use a unified command execution result for all outcomes

- **Decision**: Make dispatcher and resolver return a single structured
  execution result for success, clarification-required, confirmation-required,
  rejection, and failure cases.
- **Rationale**: Downstream layers currently receive strings, dictionaries, or
  `None`, which makes runtime behavior brittle. A unified result model directly
  satisfies the spec's structured-outcome requirements.
- **Alternatives considered**:
  - Continue returning mixed strings and dictionaries: rejected because it
    forces runtime consumers to infer semantics from shape.
  - Return exceptions for rejection and clarification: rejected because these
    are expected user-flow outcomes, not exceptional failures.

## Decision: Separate protected system commands through policy, not a new runtime path

- **Decision**: Classify system commands at parse time, apply stronger
  validation for all system actions, and require explicit confirmation for the
  high-consequence subset (`stop_system` and `reset_settings`) before resolver
  execution.
- **Rationale**: This preserves the current shared dispatch pipeline while
  giving risky commands their own safeguards and auditability.
- **Alternatives considered**:
  - Build a completely separate runtime loop for system commands: rejected
    because it is too heavy for this phase.
  - Require confirmation for every system command: rejected because it adds too
    much friction for lower-risk actions such as status checks.

## Decision: Treat face-to-emotion flow as the primary follow-up context case

- **Decision**: Use `recognize_face` followed by `recognize_emotion` as the
  canonical one-turn follow-up context flow, while designing the context model
  so it can safely support similar future follow-ups.
- **Rationale**: This is the clearest existing example in the current codebase
  where follow-up interpretation depends on prior command output.
- **Alternatives considered**:
  - Keep session context indefinitely: rejected by clarification and because it
    increases stale-context risk.
  - Clear context immediately after every command: rejected because it would
    break the existing useful face-to-emotion workflow.

## Decision: Validate with curated bilingual regression tiers

- **Decision**: Add unit coverage for parse and resolve rules, integration
  coverage for dispatcher plus runtime-facing structured outcomes, and smoke
  scenarios for representative GUI and console command flows.
- **Rationale**: The command layer is safety-sensitive and spans fuzzy
  matching, routing, and user-visible behavior. Layered regression coverage is
  needed to protect both correctness and parity.
- **Alternatives considered**:
  - Manual spot checks only: rejected because they cannot prove false-positive
    protection or mode parity.
  - Unit tests only: rejected because the structured result contract must also
    hold when invoked through dispatch and runtime normalization.
