# Data Model: Arabic, Bilingual Canonicalization, and Safety Confidence Hardening

## VariantMappingRule

**Purpose**: Defines one curated supported phrase variant that maps a spoken
Arabic, bilingual, or phonetic form to an existing command meaning without
expanding executable scope.

**Fields**:
- `rule_id`: Stable identifier such as `ar.ocr.eqra_al_nass`.
- `source_phrase`: The supported spoken variant after normalization.
- `canonical_command_text`: Parser-ready command text tied to an existing
  command meaning.
- `intent_id`: Existing supported parser intent.
- `variant_type`: `arabic | egyptian_arabic | bilingual | phonetic |
  stt_mistake`.
- `risk_level`: `normal | elevated | protected`.
- `language_scope`: `arabic | english | bilingual`.
- `enabled_by_default`: `true` for shipped curated variants.
- `notes`: Optional human-readable governance note.

**Validation Rules**:
- `canonical_command_text` must map to an already supported command boundary.
- New rules must not create new intent IDs or broaden protected-command scope.
- Duplicate `source_phrase` entries are not allowed after normalization.
- `stt_mistake` and `phonetic` rules must stay auditable and intentionally
  bounded.

**Relationships**:
- Consumed by `NormalizedCommandCandidate`.
- Audited through tests and command-inventory reviews.

## TextIntegrityAssessment

**Purpose**: Represents whether recognized text is trustworthy enough to enter
the executable command path.

**Fields**:
- `assessment_id`
- `source_text_present`
- `integrity_status`: `trusted | normalized | corrupted | mojibake |
  unexpected_unicode | empty`.
- `failure_reason`: `replacement_character | unexpected_unicode |
  mojibake_pattern | not_normalized | language_mismatch | missing`.
- `requires_safe_refusal`: Boolean.
- `requires_retry_only`: Boolean.
- `field_safe`: `true` by default.

**Validation Rules**:
- `integrity_status=corrupted` or `mojibake` must prevent direct execution.
- Protected-command flows with failed integrity must refuse rather than
  continue toward execution.
- `field_safe` must remain `true` in default diagnostics.

**Relationships**:
- Produced before or during `NormalizedCommandCandidate` construction.
- Influences `SafetyDecisionRecord`.

## NormalizedCommandCandidate

**Purpose**: Captures the parser-ready command representation emitted by
`core/command_post_processing.py` after normalization and curated mapping.

**Fields**:
- `candidate_id`
- `source_transcript_ref`
- `normalized_transcript_ref`
- `canonical_command_text`
- `integrity_status`
- `substitution_ids`
- `high_impact_substitution`
- `ambiguity_flags`
- `language_hints`
- `matched_variant_rule_ids`
- `dictionary_mode`
- `closed_vocabulary_id`
- `post_processing_status`: `unchanged | normalized | rejected |
  constrained_retry`.
- `field_safe`
- `raw_user_content_present`

**Validation Rules**:
- `post_processing_status=normalized` or `unchanged` requires a non-empty
  `canonical_command_text`.
- `post_processing_status=rejected` must not emit executable parser-ready
  text.
- Default diagnostics must use field-safe transcript references or omit
  transcript fields rather than exposing raw utterance content.
- `constrained_retry` is valid only for closed-vocabulary flows.
- `high_impact_substitution=true` requires at least one substitution or
  variant mapping that materially changes command interpretation.

**Relationships**:
- Consumes `VariantMappingRule` and `TextIntegrityAssessment`.
- Feeds parser scoring and runtime confidence policy.
- Summarized by `SafetyDecisionRecord`.

## ConfidenceEvidenceEnvelope

**Purpose**: Packages the field-safe recognition and canonicalization signals
used by runtime policy to decide execute, confirm, retry, or refuse.

**Fields**:
- `evidence_id`
- `recognition_source`
- `confidence_available`
- `confidence_score`
- `confidence_band`
- `detected_language`
- `selected_language`
- `language_mismatch`
- `alternative_conflict`
- `parser_accepted`
- `stable_supported_candidate`
- `protected_command`
- `medium_risk_candidate`
- `fallback_attempted`
- `failure_reason_code`

**Validation Rules**:
- `confidence_band` must be one of `high | medium | low | missing_confidence`.
- `stable_supported_candidate=false` prevents confirmation-based execution
  escalation for medium-risk flows.
- `language_mismatch=true` or `alternative_conflict=true` must stay visible to
  downstream safety decisions.

**Relationships**:
- Combines `CommandRecognitionResult`, parser output, and
  `NormalizedCommandCandidate`.
- Drives `SafetyDecisionRecord`.

## SafetyDecisionRecord

**Purpose**: Defines the machine-readable runtime outcome explaining whether a
command was executed, confirmed, retried, refused, or rejected safely.

**Fields**:
- `decision_id`
- `intent_id`
- `decision_action`: `execute | confirm | retry | refuse | fallback`.
- `decision_band`
- `reason_code`
- `confirmation_required`
- `retry_count`
- `protected_command`
- `stable_supported_candidate`
- `spoken_guidance_surface`
- `field_safe_metadata`
- `payload`

**Validation Rules**:
- Protected commands never use `execute` directly when `confirmation_required`
  should be true.
- `decision_action=confirm` requires `stable_supported_candidate=true`.
- Corrupted protected-command attempts must resolve to `refuse`, not `retry`.
- `field_safe_metadata` must exclude raw utterance content by default.

**Relationships**:
- Consumes `ConfidenceEvidenceEnvelope`.
- Produces runtime guidance and diagnostics.
- May lead into `ConfirmationDialogTurn`.

## ConfirmationDialogTurn

**Purpose**: Represents one multilingual confirmation exchange for a protected
or medium-risk command after a stable candidate survives normalization.

**Fields**:
- `turn_id`
- `pending_intent_id`
- `closed_vocabulary_id`
- `prompt_surface_id`
- `accepted_language_scopes`
- `response_outcome`: `affirmative | negative | cancel | ambiguous |
  unmatched`.
- `safe_precedence_applied`
- `final_resolution`: `execute | decline | retry | expire`.

**Validation Rules**:
- Protected-command confirmation requires a closed-vocabulary-compatible
  interpretation path.
- `safe_precedence_applied=true` is allowed when cancel or negative markers
  outrank affirmative markers in mixed replies.
- `final_resolution=execute` requires `response_outcome=affirmative`.

**Relationships**:
- Triggered by `SafetyDecisionRecord`.
- Reuses shared dialog-policy helpers and closed-vocabulary configuration.

## State Transitions

- `raw transcript -> TextIntegrityAssessment(trusted|normalized)` when the
  text passes Unicode and mojibake safety checks.
- `raw transcript -> TextIntegrityAssessment(corrupted|mojibake|empty)` when
  the text must stay non-executable.
- `trusted input -> NormalizedCommandCandidate(unchanged|normalized)` when
  supported normalization or curated mapping yields parser-ready text.
- `trusted input -> NormalizedCommandCandidate(rejected|constrained_retry)`
  when the text is out of scope, closed-vocabulary mismatched, or unsafe.
- `NormalizedCommandCandidate -> ConfidenceEvidenceEnvelope` after parser and
  recognition metadata are combined.
- `ConfidenceEvidenceEnvelope -> SafetyDecisionRecord(execute)` for clean
  low-risk cases with stable support.
- `ConfidenceEvidenceEnvelope -> SafetyDecisionRecord(confirm)` for protected
  or medium-risk cases with stable supported candidates.
- `ConfidenceEvidenceEnvelope -> SafetyDecisionRecord(retry|refuse|fallback)`
  for corrupted, ambiguous, language-mismatch, unstable-candidate, or
  low-confidence cases.
- `SafetyDecisionRecord(confirm) -> ConfirmationDialogTurn` for bilingual
  affirmative/negative/cancel handling before execution.
