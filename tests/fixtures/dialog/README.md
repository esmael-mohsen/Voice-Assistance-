# Phase 16 Guided Dialog Fixtures

This folder stores metadata-only fixture definitions used to validate guided
voice UX behavior without shipping raw user utterances.

## Required Scenario Coverage

- Allowed early-answer capture during onboarding and low-risk settings prompts.
- Protected confirmation prompts that block early barge-in until spoken once.
- Closed-vocabulary turns with valid aliases, near misses, and out-of-domain
  speech.
- Prompt-echo suppression where assistant prompt text is captured by STT.
- Name-capture confirmation recovery, including reject/cancel cases.
- Retry exhaustion paths that continue with safe defaults or exit gracefully.

## Evidence Rules

- Field-safe artifacts only by default.
- No raw user utterance text in stored fixture outputs.
- Every run should report completion status, retries, accepted barge-ins,
  prompt-echo suppressions, out-of-domain rejections, and fallback/exit reason.

