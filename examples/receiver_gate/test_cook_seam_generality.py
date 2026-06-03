"""Generality tests for the cook seam.

The seam is `AdmissionInput → AdmissionPolicy.accepts → AdmissionVerdict`,
with `WicketAdmissionPolicy` cooking AdmissionInput into a Wicket Intent
under the hood and `LocalAdmissionPolicy` shortcutting to a direct
verdict. A single cook-table entry could be an accidentally perfect
specimen; these tests prove the seam tolerates at least two entries
with different claim_type, witness_kind, and witness_anchor without
forcing per-entry code paths or vocabulary leakage.

Specimen pair:
  restart_service + failed_health_probe + probe-service   (slice 1)
  flush_cache     + cache_pressure_signal + metrics-service (this slice)

What is NOT tested here — and what to report instead:
  end-to-end flow through `ReceiverGate.handle` for flush_cache. The
  receiver-gate's HMAC fixture (TRUSTED_PROBE_KEY) is single-anchor by
  fixture choice; verifying a metrics-service witness would require
  the gate to grow a trust-anchor table mapping anchor_id → key. That
  is anchor-config (receiver mechanics), not policy or cook shape.
  The cook seam is unaffected. See README "Finding: HMAC fixture is
  single-anchor" for the documented limitation.
"""
from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from admission import (
    AdmissionInput,
    AdmissionVerdict,
    LocalAdmissionPolicy,
)
from wicket_policy import (
    DEFAULT_COOK_TABLE,
    WicketAdmissionPolicy,
    find_wicket_binary,
)


NOW = datetime(2026, 6, 3, 9, 0, 0, tzinfo=UTC)
CACHE_TARGET = "user-sessions"
SERVICE_TARGET = "api-01"


def _flush_cache_input(
    *,
    witness_kind: str = "cache_pressure_signal",
    witness_anchor: str = "metrics-service",
    target: str = CACHE_TARGET,
) -> AdmissionInput:
    return AdmissionInput(
        claim_type="flush_cache",
        witness_kind=witness_kind,
        witness_anchor=witness_anchor,
        target=target,
        now=NOW,
    )


def _restart_service_input() -> AdmissionInput:
    return AdmissionInput(
        claim_type="restart_service",
        witness_kind="failed_health_probe",
        witness_anchor="probe-service",
        target=SERVICE_TARGET,
        now=NOW,
    )


needs_wicket = pytest.mark.skipif(
    find_wicket_binary() is None,
    reason="wicket binary not found; set WICKET_BIN or build wicket",
)


# -----------------------------------------------------------------------------
# Cook-table parity
# -----------------------------------------------------------------------------


def test_cook_tables_share_the_same_claim_type_keys() -> None:
    """LocalAdmissionPolicy and WicketAdmissionPolicy must remain
    parallel on the keys they recognize. A divergence would mean
    swapping one implementation for the other silently changes
    admission verdicts."""
    local_keys = set(LocalAdmissionPolicy.REQUIRED_WITNESS.keys())
    wicket_keys = set(DEFAULT_COOK_TABLE.keys())
    assert local_keys == wicket_keys, (
        f"cook tables diverged: local={local_keys}, wicket={wicket_keys}"
    )


def test_cook_tables_agree_on_required_witness_combinations() -> None:
    """For every shared claim_type, both implementations must agree
    on the (witness_kind, witness_anchor) precondition."""
    for claim_type, (kind, anchor) in LocalAdmissionPolicy.REQUIRED_WITNESS.items():
        recipe = DEFAULT_COOK_TABLE[claim_type]
        assert recipe.required_witness_kind == kind, (
            f"witness_kind diverged for {claim_type}"
        )
        assert recipe.required_witness_anchor == anchor, (
            f"witness_anchor diverged for {claim_type}"
        )


# -----------------------------------------------------------------------------
# Local: admits when matching, refuses when one field differs
# -----------------------------------------------------------------------------


def test_local_admits_flush_cache_when_all_fields_match() -> None:
    verdict = LocalAdmissionPolicy().accepts(_flush_cache_input())
    assert verdict.status == "accepted"


def test_local_refuses_flush_cache_with_wrong_witness_kind() -> None:
    verdict = LocalAdmissionPolicy().accepts(
        _flush_cache_input(witness_kind="failed_health_probe")
    )
    assert verdict.status == "refused"
    assert "failed_health_probe" in verdict.reason


def test_local_refuses_flush_cache_with_wrong_witness_anchor() -> None:
    verdict = LocalAdmissionPolicy().accepts(
        _flush_cache_input(witness_anchor="probe-service")
    )
    assert verdict.status == "refused"
    assert "probe-service" in verdict.reason


def test_local_still_admits_restart_service() -> None:
    """The first entry's behavior is unchanged by adding the second."""
    verdict = LocalAdmissionPolicy().accepts(_restart_service_input())
    assert verdict.status == "accepted"


# -----------------------------------------------------------------------------
# Wicket: cook + invoke for both entries
# -----------------------------------------------------------------------------


def test_wicket_refuses_flush_cache_with_wrong_witness_kind_without_invoking() -> None:
    """Without a binary, the cook precondition still refuses cleanly."""
    policy = WicketAdmissionPolicy(wicket_bin="/nonexistent/wicket")
    verdict = policy.accepts(_flush_cache_input(witness_kind="failed_health_probe"))
    assert verdict.status == "refused"


def test_wicket_refuses_flush_cache_with_wrong_witness_anchor_without_invoking() -> None:
    policy = WicketAdmissionPolicy(wicket_bin="/nonexistent/wicket")
    verdict = policy.accepts(_flush_cache_input(witness_anchor="probe-service"))
    assert verdict.status == "refused"


@needs_wicket
def test_wicket_admits_flush_cache_when_cooked_through_real_wicket() -> None:
    """End-to-end through wicket: the cook produces an Intent for the
    second entry without any code path changes in `accepts()`, and
    Wicket evaluates it as authorized."""
    verdict = WicketAdmissionPolicy().accepts(_flush_cache_input())
    assert verdict.status == "accepted"
    assert "wicket authorized" in verdict.reason


@needs_wicket
def test_wicket_still_admits_restart_service_end_to_end() -> None:
    verdict = WicketAdmissionPolicy().accepts(_restart_service_input())
    assert verdict.status == "accepted"


# -----------------------------------------------------------------------------
# Cook produces normalized intent for the second entry too — no leakage
# -----------------------------------------------------------------------------


def test_cooked_intent_for_flush_cache_has_no_wlp_wire_fields() -> None:
    """The Wicket Intent cooked for flush_cache must carry only
    Wicket-vocabulary fields. WLP wire vocabulary
    (custody/witness_ref/receipt_class/artifact_hash) must not
    appear anywhere in the intent."""
    policy = WicketAdmissionPolicy()
    recipe = DEFAULT_COOK_TABLE["flush_cache"]
    intent = policy._cook_intent(_flush_cache_input(), recipe)

    import json as _json

    intent_json = _json.dumps(intent)
    for forbidden in (
        "custody",
        "witness_ref",
        "receipt_class",
        "artifact_hash",
        "ClaimReceipt",
        "ProbeReceipt",
    ):
        assert forbidden not in intent_json, (
            f"cooked intent leaked WLP wire field: {forbidden!r}\n{intent_json}"
        )


def test_cooked_intent_carries_recipe_specific_rule_text() -> None:
    """Different cook-table entries must produce different
    `claimed_basis.rule` text. If both entries collapsed to the same
    Wicket rule, Wicket would conflate them — a real semantic bug."""
    policy = WicketAdmissionPolicy()
    rs_intent = policy._cook_intent(
        _restart_service_input(), DEFAULT_COOK_TABLE["restart_service"]
    )
    fc_intent = policy._cook_intent(
        _flush_cache_input(), DEFAULT_COOK_TABLE["flush_cache"]
    )
    assert rs_intent["claimed_basis"]["rule"] != fc_intent["claimed_basis"]["rule"]
    assert "failed_health_probe" in rs_intent["claimed_basis"]["rule"]
    assert "cache_pressure_signal" in fc_intent["claimed_basis"]["rule"]


# -----------------------------------------------------------------------------
# Structural: ReceiverGate has no claim-type case-switching
# -----------------------------------------------------------------------------


def test_receiver_gate_handle_is_policy_agnostic_at_source_level() -> None:
    """ReceiverGate.handle() does mechanics + adapter + policy. It
    must not contain `if claim_type ==` branches: every claim_type
    is decided by the policy. This is the structural counterpart to
    the per-policy admission tests."""
    from receiver_gate import ReceiverGate

    source = inspect.getsource(ReceiverGate.handle)
    assert 'claim_type ==' not in source.replace(' ', ''), (
        "ReceiverGate.handle contains explicit claim_type comparison — "
        "decisions should route through the policy, not the gate"
    )
    assert '"restart_service"' not in source, (
        "ReceiverGate.handle hardcodes 'restart_service' — should be policy-decided"
    )
    assert '"flush_cache"' not in source, (
        "ReceiverGate.handle hardcodes 'flush_cache' — should be policy-decided"
    )


def test_receiver_gate_routes_arbitrary_claim_type_through_policy() -> None:
    """A spy policy receives whatever AdmissionInput.claim_type the
    adapter produced, regardless of the value. The gate does not
    pre-filter on claim_type."""
    from receiver_gate import (
        ReceiverGate,
        make_probe_receipt,
        make_restart_claim,
    )

    captured: list[str | None] = []

    class _SpyAcceptAny:
        def accepts(self, admission_input: AdmissionInput) -> AdmissionVerdict:
            captured.append(admission_input.claim_type)
            return AdmissionVerdict("accepted", "spy accepts")

    gate = ReceiverGate(policy=_SpyAcceptAny())
    witness = make_probe_receipt("api-01", NOW)
    claim = make_restart_claim("api-01", witness_hash=witness["custody"]["artifact_hash"])
    # Mutate the claim_type to something the gate has never heard of.
    claim["subject"]["claim_type"] = "vacuum_telemetry"

    gate.handle(claim, {witness["custody"]["artifact_hash"]: witness}, now=NOW)

    assert captured == ["vacuum_telemetry"], (
        "ReceiverGate filtered or rewrote claim_type instead of routing it"
    )


# -----------------------------------------------------------------------------
# Documented finding: single-anchor HMAC fixture
# -----------------------------------------------------------------------------


def test_receiver_gate_hmac_fixture_remains_single_anchor() -> None:
    """Documenting the surfaced finding from this slice: the
    receiver-gate's HMAC verification is single-anchor by fixture
    choice. Generalizing the gate to verify multiple anchors (e.g.,
    metrics-service in addition to probe-service) is a separate
    slice — anchor-config, distinct from cook-seam shape.

    This test pins the current state. If the gate grows a real
    trust-anchor table, this test should be updated or replaced to
    reflect the generalized verification surface.
    """
    from receiver_gate import TRUSTED_PROBE_ID, verify_probe_receipt

    assert TRUSTED_PROBE_ID == "probe-service"
    # No `TRUSTED_ANCHORS` table or per-anchor key registry exists.
    import receiver_gate

    assert not hasattr(receiver_gate, "TRUSTED_ANCHORS"), (
        "Gate appears to have grown a trust-anchor table; update this "
        "documentation test and add multi-anchor coverage for flush_cache."
    )
    # And the verifier is still HMAC-shaped, not a registry lookup.
    src = inspect.getsource(verify_probe_receipt)
    assert "TRUSTED_PROBE_KEY" in src
