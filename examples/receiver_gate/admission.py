"""Receiver-side admission seam.

Boundary object between WLP packet evidence and Wicket-shaped admission
policy. WLP supplies packet/evidence facts. The receiver's adapter
normalizes those facts into `AdmissionInput`. A Wicket-shaped policy
evaluates `AdmissionInput`. The receiver acts on the verdict.

Doctrinal invariants this module preserves:

- The policy never sees raw WLP wire JSON. It sees only the normalized
  `AdmissionInput` produced by a receiver-side adapter.
- WLP code does not import this module's policy implementation directly;
  WLP emits packets, and the receiver is what couples to admission.
- `AdmissionInput` is admission-shaped, not WLP-shaped. Field names
  describe a receiver-side admission request, not a wire envelope.
- `AdmissionVerdict` is authorization/admission-shaped, not WLP-ontology.

A real receiver would back `AdmissionPolicy` with a Wicket bridge (e.g.,
shell out to `wicket check` or a Wicket FFI binding). The fixture-local
`LocalAdmissionPolicy` here is a Wicket-shaped stand-in for the demo.
"""
from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Literal, Protocol


AdmissionStatus = Literal["accepted", "refused", "unsupported"]


@dataclasses.dataclass(frozen=True)
class AdmissionInput:
    """Normalized receiver-side admission request.

    Built from packet facts by the receiver's adapter. Carries only the
    normalized fields an admission policy needs — no wire envelopes,
    no signatures, no nested receipt structure.
    """

    claim_type: str | None
    witness_kind: str | None
    witness_anchor: str | None
    target: str | None
    now: datetime


@dataclasses.dataclass(frozen=True)
class AdmissionVerdict:
    status: AdmissionStatus
    reason: str


class AdmissionPolicy(Protocol):
    """Receiver-side admission policy surface.

    Implementations decide admissibility from `AdmissionInput` alone.
    They MUST NOT consume raw WLP wire shape; the adapter is the
    boundary.
    """

    def accepts(self, admission_input: AdmissionInput) -> AdmissionVerdict: ...


class LocalAdmissionPolicy:
    """Fixture-local Wicket-shaped admission policy.

    Mirrors what a Wicket-backed policy would decide for the receiver
    gate's demonstrated lie-classes. A real deployment would replace
    this with a Wicket bridge (see `wicket_policy.py`).

    `REQUIRED_WITNESS` must stay parallel to
    `wicket_policy.DEFAULT_COOK_TABLE`: a receiver swapping one
    implementation for the other should see the same admission
    decisions on the keys both implementations recognize.

    The point of the seam is that this class's signature accepts only
    `AdmissionInput`, never a WLP packet dict.
    """

    REQUIRED_WITNESS = {
        "restart_service": ("failed_health_probe", "probe-service"),
        "flush_cache": ("cache_pressure_signal", "metrics-service"),
    }

    def accepts(self, admission_input: AdmissionInput) -> AdmissionVerdict:
        required = self.REQUIRED_WITNESS.get(admission_input.claim_type or "")
        if required is None:
            return AdmissionVerdict("unsupported", "unsupported claim type")
        want_kind, want_anchor = required
        if admission_input.witness_kind != want_kind:
            return AdmissionVerdict(
                "refused",
                f"witness kind {admission_input.witness_kind!r} does not satisfy admission policy",
            )
        if admission_input.witness_anchor != want_anchor:
            return AdmissionVerdict(
                "refused",
                f"witness anchor {admission_input.witness_anchor!r} does not satisfy admission policy",
            )
        return AdmissionVerdict("accepted", "admission policy satisfied")
