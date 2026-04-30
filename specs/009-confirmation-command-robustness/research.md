# Research: Confirmation, Clarification, and Command Robustness

## Decision: Use normalized token and phrase-family matching for dialog intent

- **Decision**: Replace exact full-string yes and no checks with normalized
  token and phrase-family matching for approved affirmative, negative, and
  cancel utterances in Arabic and English.
- **Rationale**: Current exact equality in the resolver is brittle under STT
  variation and fails on common filler-heavy replies such as `yes please` or
  `aywa tamam`, even when user intent is clear.
- **Alternatives considered**:
  - Keep exact full-string matching: rejected because it misses normal STT
    variation and creates avoidable confirmation failures.
  - Use broad fuzzy matching over arbitrary user text: rejected because
    protected commands need deterministic, safety-first boundaries.

## Decision: Negative or cancel cues always take precedence over affirmative cues

- **Decision**: When the same utterance contains both affirmative and negative
  or cancel signals, resolve the final outcome to the safe non-executing path.
- **Rationale**: Mixed confirmations are ambiguous in practice, and the safest
  interpretation is to prevent accidental execution of protected actions.
- **Alternatives considered**:
  - Choose the first matched cue: rejected because STT token order is not
    reliable enough for safety decisions.
  - Retry by default for every mixed response: rejected because an explicit
    cancel must remain easy and reliable to trigger.

## Decision: Centralize yes, no, and cancel interpretation behind one shared policy

- **Decision**: Implement one shared dialog-interpretation boundary that is
  reused by protected-command confirmation and comparable onboarding or
  confirmation prompts.
- **Rationale**: Phase 9 explicitly requires consistent behavior across runtime
  flows, and duplicating phrase parsing would invite drift between resolver and
  onboarding safety behavior.
- **Alternatives considered**:
  - Keep separate resolver and runtime phrase lists: rejected because they will
    diverge over time and create inconsistent user experiences.
  - Move all dialog interpretation into the UI layer: rejected because runtime
    behavior must remain headless-first.

## Decision: Clarification prompts must speak supported choices explicitly

- **Decision**: Parameter-required clarification prompts for settings-style
  intents should list the currently supported options instead of using generic
  open-ended retry prompts.
- **Rationale**: Users should not need to guess hidden valid values during a
  speech-only flow, especially in an accessibility-critical assistant.
- **Alternatives considered**:
  - Continue generic retry prompts: rejected because they force trial-and-error
    and hide the allowed choices.
  - Accept open free-form clarification values: rejected because this phase is
    intentionally scoped to explicit supported-option flows.

## Decision: Bound clarification to one initial prompt plus two retries

- **Decision**: Allow one clarification prompt followed by at most two retry
  attempts before ending in a safe stop.
- **Rationale**: This preserves accessibility and momentum without trapping the
  user in an indefinite loop or drifting into unintended settings changes.
- **Alternatives considered**:
  - Stop after one failed clarification: rejected because modest STT variance
    should still get a fair retry path.
  - Retry indefinitely: rejected because it creates poor UX and weakens safe
    failure behavior.

## Decision: Clear unrelated follow-up context when confirmation or clarification activates

- **Decision**: Entering a pending confirmation or clarification flow should
  clear unrelated stale follow-up state before the new dialog becomes active.
- **Rationale**: Follow-up context is useful for adjacent commands, but it must
  not satisfy or corrupt a higher-priority safety dialog from an earlier turn.
- **Alternatives considered**:
  - Keep all follow-up context until explicitly consumed: rejected because
    stale context can leak into unrelated dialog decisions.
  - Disable follow-up context globally during Phase 9: rejected because the
    feature only needs state isolation, not removal of follow-up behavior.

## Decision: Reuse approved prompt surfaces and add clarification-specific surfaces only if needed

- **Decision**: Keep confirmation guidance routed through the existing critical
  prompt catalog and extend it with clarification-specific approved surfaces
  only when the current catalog cannot express explicit supported choices.
- **Rationale**: Phase 7 already established localization integrity guarantees,
  and Phase 9 should strengthen dialog robustness without bypassing approved
  prompt infrastructure.
- **Alternatives considered**:
  - Embed new prompt strings directly in resolver logic: rejected because it
    would bypass localization integrity gates.
  - Rephrase clarification prompts ad hoc in each command branch: rejected
    because consistency and testability matter more than local convenience.

## Decision: Validate dialog robustness with a targeted regression matrix

- **Decision**: Add unit, integration, and smoke coverage for Arabic and
  English phrase variants, cancellations, mixed yes and cancel utterances,
  clarification retry bounds, and follow-up isolation.
- **Rationale**: The feature crosses pure parsing, session state, runtime flow,
  and localization surfaces, so a single-path test set would not protect the
  behavior reliably.
- **Alternatives considered**:
  - Test only pure helper functions: rejected because dialog-state transitions
    and spoken outputs are part of the contract.
  - Test only protected confirmation: rejected because clarification and
    follow-up isolation are explicit feature requirements.
