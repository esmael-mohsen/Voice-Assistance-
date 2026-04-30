# Research: Arabic, Bilingual Canonicalization, and Safety Confidence Hardening

## Decision: Keep command understanding on the deterministic post-processing -> parser -> runtime-policy path

- **Decision**: Build Phase 20 by extending
  `core/command_post_processing.py`, `core/parser.py`, and
  `core/assistant_runtime.py` rather than introducing a separate intent model
  or a new command-resolution subsystem.
- **Rationale**: The repo already has the right architecture seams:
  post-processing produces parser-ready text, the parser ties execution to the
  supported command catalog, and runtime confidence policy owns execute,
  confirm, retry, and refuse outcomes. Extending those seams preserves the
  constitution's incremental-evolution and replaceable-interface principles.
- **Alternatives considered**:
  - Add an open-domain language model or semantic intent layer: rejected
    because the phase explicitly forbids widening command scope through a new
    language model.
  - Move command canonicalization into the parser alone: rejected because
    post-processing already owns transcript normalization and metadata capture.

## Decision: Govern Arabic, bilingual, and Arabizi support through a curated allowlist tied to existing command boundaries

- **Decision**: Keep supported Arabic, Egyptian-Arabic, bilingual, and
  phonetic variants in curated repo-hosted inventories that map only to
  already supported command meanings and intent IDs.
- **Rationale**: The spec requires broader spoken coverage without widening
  executable scope. A curated allowlist keeps new phrases auditable, testable,
  and bounded to the current command catalog while avoiding false positives
  from vague or speculative matches.
- **Alternatives considered**:
  - Learn executable variants from field utterances automatically: rejected
    because the feature must remain field-safe and must not auto-learn new
    executable phrases by default.
  - Accept any close Arabic phonetic approximation: rejected because it would
    increase false positives for protected or medium-risk commands.

## Decision: Treat corrupted Arabic-like text and mojibake as integrity failures before parser execution

- **Decision**: Run integrity checks early and classify corrupted Arabic-like
  text, mojibake, and unexpected Unicode as non-executable before parser
  scoring or resolver execution.
- **Rationale**: Parser fuzz matching is useful for supported noisy variants,
  but it becomes unsafe if clearly corrupted text is allowed into the
  executable command path. Early rejection also aligns with the existing
  `core/text_integrity.py` helpers and the spec's requirement that corrupted
  protected-command attempts refuse safely.
- **Alternatives considered**:
  - Let the parser reject corrupted text indirectly through thresholds:
    rejected because fuzzy matching could still surface unstable candidates.
  - Strip unknown characters and continue execution: rejected because it can
    silently change command meaning.

## Decision: Preserve field-safe normalization traces instead of opaque replacements

- **Decision**: Continue emitting structured normalization traces such as
  `substitution_ids`, integrity status, ambiguity flags, language mismatch
  markers, and alternative-conflict markers so downstream safety policy can
  explain major command decisions without storing raw utterance content.
- **Rationale**: Phase 20 is not only about correctness; it also needs
  observable and privacy-preserving decision trails. The existing command
  models already support field-safe metadata, so expanding those traces is the
  lowest-risk way to keep diagnostics meaningful.
- **Alternatives considered**:
  - Log only the final canonical command text: rejected because it hides major
    substitutions and ambiguity reasons.
  - Persist raw transcripts for debugging: rejected because it violates the
    default privacy boundary.

## Decision: Drive medium-risk confirmation from stable-candidate evidence, not confidence alone

- **Decision**: Extend runtime confidence decisions so medium-risk and
  ambiguity-sensitive flows look at the combined evidence set: confidence
  band, conflicting alternatives, language mismatch, corruption status, and
  high-impact substitutions. Confirm only when a stable supported candidate
  remains; otherwise retry or refuse.
- **Rationale**: Confidence alone is not a safe proxy for command intent in
  bilingual and corrupted-text cases. The existing runtime already evaluates
  ambiguity and language mismatch, so Phase 20 should refine that decision
  rather than replacing it.
- **Alternatives considered**:
  - Confirm every medium-confidence candidate: rejected because it adds noise
    and can still push unstable interpretations toward execution.
  - Retry every mismatch or substitution case: rejected because some medium-
    risk commands have enough stable evidence to justify confirmation instead.

## Decision: Keep protected-command confirmation multilingual and closed-vocabulary-aware

- **Decision**: Preserve protected-command confirmation through the existing
  bilingual `dialog_policy.py` and `closed_vocabulary.py` surfaces instead of
  adding parser-only confirmation phrase handling.
- **Rationale**: Protected-command safety already depends on shared yes/no/
  cancel interpretation with safe precedence. Phase 20 needs that behavior to
  remain consistent across Arabic, English, and mixed replies after command
  canonicalization expands.
- **Alternatives considered**:
  - Put confirmation phrase handling inside the parser catalog: rejected
    because confirmation is dialog state, not a normal executable intent.
  - Accept free-form positive sentiment as confirmation: rejected because it
    weakens protected-command safeguards.

## Decision: Validate Phase 20 with fixture-driven tests and fake recognition metadata rather than live providers

- **Decision**: Use repo fixtures and monkeypatched recognition metadata for
  supported Arabic commands, mixed-language variants, corrupted text,
  alternative conflicts, and language mismatch cases instead of relying on
  live cloud credentials in the default test path.
- **Rationale**: The phase focuses on deterministic canonicalization and
  safety policy. Those behaviors should remain testable offline and in CI,
  while still reflecting the metadata shapes returned by cloud-primary and
  strict-fallback recognition.
- **Alternatives considered**:
  - Require live Google Cloud runs for every validation pass: rejected because
    it makes regression testing fragile and credential-dependent.
  - Test only happy-path supported phrases: rejected because the feature is
    largely about rejecting unsafe or unstable inputs correctly.
