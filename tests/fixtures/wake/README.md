# Phase 15 Wake Replay Fixtures

This folder documents replay fixture expectations for
`specs/015-wake-telemetry-qualification`.

## Fixture Intention

- Keep wake replay fixtures metadata-first for local and CI validation.
- Cover quiet, noisy, and bilingual wake conditions.
- Exercise degraded-provider and repeated-fault recovery behavior.
- Keep artifact references local by default under `artifacts/<run-id>/speech/`.

## Wake Alias Catalog

- Canonical: `hi egb`, `marhaba`
- English variants: `hi agency`, `hi hgb`, `hi e g b`
- Arabic variants (romanized for fixture readability): `marhaba`, `ahlan e g b`, `hala e g b`
- Non-wake controls: `hello assistant`, `what time is it`, `background chatter`

## Replay Scenario Matrix

- `quiet_wake`: expect direct acceptance and wake-to-listen latency telemetry.
- `noisy_wake`: expect bounded rejection with review telemetry.
- `bilingual_wake`: expect accepted wake for approved multilingual alias.
- `degraded_provider`: expect recovery-reset telemetry with truthful guidance.
- `repeated_fault`: expect recovery-reset and clipped-retry telemetry.

## Evidence Routing

- Runtime telemetry must persist locally first.
- External sink failures must not block local evidence completeness.
- Qualification evidence references should resolve inside the candidate bundle.
