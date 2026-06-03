"""Tests for the real Wicket-backed AdmissionPolicy.

Six acceptance tests for the receiver-mediated seam's real wiring:

1. WicketAdmissionPolicy receives only AdmissionInput, never a raw
   WLP packet — structural / type contract.
2. Supported restart claim + valid witness → permit (Wicket
   authorized).
3. Unsupported claim → unsupported (cook-table miss; no Wicket call).
4. Wrong witness kind → refused (cook precondition; no Wicket call).
5. Wicket denial reason survives into AdmissionVerdict.reason
   (induced by configuring the gate with insufficient standing for
   execute).
6. WLP library still has no Wicket dependency — grep wlp/Cargo.toml
   and wlp/src for any wicket reference.

Tests that actually invoke Wicket are skipped when no usable binary
is found.
"""
from __future__ import annotations

import pathlib
import subprocess
from datetime import UTC, datetime

import pytest

from admission import AdmissionInput, AdmissionVerdict
from wicket_policy import (
    DEFAULT_COOK_TABLE,
    WicketAdmissionPolicy,
    find_wicket_binary,
)


NOW = datetime(2026, 6, 1, 19, 0, 0, tzinfo=UTC)
TARGET = "api-01"


def _good_input() -> AdmissionInput:
    return AdmissionInput(
        claim_type="restart_service",
        witness_kind="failed_health_probe",
        witness_anchor="probe-service",
        target=TARGET,
        now=NOW,
    )


needs_wicket = pytest.mark.skipif(
    find_wicket_binary() is None,
    reason="wicket binary not found; set WICKET_BIN or build wicket",
)


# -----------------------------------------------------------------------------
# 1. Receives only AdmissionInput, never raw packet
# -----------------------------------------------------------------------------


def test_wicket_policy_accepts_only_admission_input() -> None:
    """Construction does not require the binary; the seam contract is
    that `accepts()` consumes `AdmissionInput`. Passing a dict-shaped
    WLP packet should fail at the boundary (attribute access on
    something that is not an AdmissionInput)."""
    policy = WicketAdmissionPolicy(wicket_bin="/nonexistent/wicket")
    raw_packet = {
        "receipt_class": "ClaimReceipt",
        "producer": "agent-a",
        "subject": {"claim_type": "restart_service", "target": TARGET},
        "witness_ref": {"artifact_hash": "deadbeef"},
    }
    with pytest.raises((AttributeError, TypeError)):
        policy.accepts(raw_packet)  # type: ignore[arg-type]


# -----------------------------------------------------------------------------
# 2. Supported restart claim + valid witness → permit
# -----------------------------------------------------------------------------


@needs_wicket
def test_supported_restart_with_valid_witness_is_permitted() -> None:
    verdict = WicketAdmissionPolicy().accepts(_good_input())
    assert verdict.status == "accepted"
    assert "wicket authorized" in verdict.reason


# -----------------------------------------------------------------------------
# 3. Unsupported claim → unsupported (no Wicket call)
# -----------------------------------------------------------------------------


def test_unsupported_claim_type_is_unsupported_without_wicket() -> None:
    """An unsupported claim type returns `unsupported` from the cook
    table miss alone — Wicket is never invoked, so this test passes
    even with no binary on the system."""
    policy = WicketAdmissionPolicy(wicket_bin="/nonexistent/wicket")
    ai = AdmissionInput(
        claim_type="delete_database",
        witness_kind="failed_health_probe",
        witness_anchor="probe-service",
        target=TARGET,
        now=NOW,
    )
    verdict = policy.accepts(ai)
    assert verdict.status == "unsupported"
    assert "unsupported claim type" in verdict.reason


# -----------------------------------------------------------------------------
# 4. Wrong witness kind → refused (no Wicket call)
# -----------------------------------------------------------------------------


def test_wrong_witness_kind_is_refused_without_wicket() -> None:
    """The cook table entry's structural precondition is checked
    before Wicket; Wicket would not have caught this (its evidence
    vocabulary does not include `failed_health_probe`)."""
    policy = WicketAdmissionPolicy(wicket_bin="/nonexistent/wicket")
    ai = AdmissionInput(
        claim_type="restart_service",
        witness_kind="load_average_sample",
        witness_anchor="probe-service",
        target=TARGET,
        now=NOW,
    )
    verdict = policy.accepts(ai)
    assert verdict.status == "refused"
    assert "load_average_sample" in verdict.reason


def test_wrong_witness_anchor_is_refused_without_wicket() -> None:
    policy = WicketAdmissionPolicy(wicket_bin="/nonexistent/wicket")
    ai = AdmissionInput(
        claim_type="restart_service",
        witness_kind="failed_health_probe",
        witness_anchor="some-other-anchor",
        target=TARGET,
        now=NOW,
    )
    verdict = policy.accepts(ai)
    assert verdict.status == "refused"
    assert "some-other-anchor" in verdict.reason


# -----------------------------------------------------------------------------
# 5. Wicket denial reason survives into AdmissionVerdict.reason
# -----------------------------------------------------------------------------


@needs_wicket
def test_wicket_denial_reason_survives_into_admission_verdict() -> None:
    """Configure the gate with `recommend` standing trying to execute.
    Wicket denies with STANDING_INSUFFICIENT_FOR_OPERATION; the
    salient reason code must appear in the AdmissionVerdict.reason
    so receivers can attribute the refusal."""
    policy = WicketAdmissionPolicy(gate_standing="recommend")
    verdict = policy.accepts(_good_input())
    assert verdict.status == "refused"
    assert "wicket denied" in verdict.reason
    assert "STANDING_INSUFFICIENT_FOR_OPERATION" in verdict.reason


# -----------------------------------------------------------------------------
# 6. WLP library has no Wicket dependency
# -----------------------------------------------------------------------------


def test_wlp_crate_has_no_wicket_dependency() -> None:
    """The WLP Rust crate must not depend on Wicket. Receiver-mediated
    integration lives in `examples/receiver_gate/`, never in the
    library surface."""
    wlp_root = pathlib.Path(__file__).resolve().parents[2]
    cargo_toml = (wlp_root / "Cargo.toml").read_text()
    assert "wicket" not in cargo_toml.lower(), (
        f"WLP Cargo.toml mentions wicket:\n{cargo_toml}"
    )
    src_dir = wlp_root / "src"
    for rs_path in src_dir.rglob("*.rs"):
        text = rs_path.read_text()
        assert "wicket" not in text.lower(), (
            f"WLP source file {rs_path} mentions wicket"
        )


# -----------------------------------------------------------------------------
# Bonus: end-to-end through ReceiverGate with the real WicketAdmissionPolicy
# -----------------------------------------------------------------------------


@needs_wicket
def test_receiver_gate_with_wicket_policy_end_to_end() -> None:
    """The full chain: WLP packet → ReceiverGate (mechanics) →
    adapt_packet_to_admission_input → WicketAdmissionPolicy → wicket
    CLI → AdmissionVerdict → HandlingReceipt. The seam holds end to
    end with the real Wicket binary."""
    from receiver_gate import ReceiverGate, make_probe_receipt, make_restart_claim

    gate = ReceiverGate(policy=WicketAdmissionPolicy())
    witness = make_probe_receipt(TARGET, NOW)
    claim = make_restart_claim(TARGET, witness_hash=witness["custody"]["artifact_hash"])
    receipt = gate.handle(
        claim, {witness["custody"]["artifact_hash"]: witness}, now=NOW
    )
    assert receipt.verdict == "accepted"
    assert receipt.mutated is True
    assert "wicket authorized" in receipt.reason
    assert gate.restart_count == 1


# -----------------------------------------------------------------------------
# Sanity: cook table is the only place that names claim_type → Wicket rule
# -----------------------------------------------------------------------------


def test_cook_table_is_the_only_admission_to_wicket_mapping() -> None:
    """Documentary assertion: the cook table is the receiver-side
    mapping from claim_type to Wicket Intent. If it grows entries,
    that is where they live — not scattered through `accepts()`."""
    assert "restart_service" in DEFAULT_COOK_TABLE
    recipe = DEFAULT_COOK_TABLE["restart_service"]
    assert recipe.required_witness_kind == "failed_health_probe"
    assert recipe.required_witness_anchor == "probe-service"
    assert recipe.intended_action == "restart_service"
    assert recipe.operation_class == "execute"


# -----------------------------------------------------------------------------
# Sanity: binary not found raises a clear error
# -----------------------------------------------------------------------------


def test_missing_wicket_binary_raises_file_not_found(monkeypatch) -> None:
    monkeypatch.delenv("WICKET_BIN", raising=False)
    policy = WicketAdmissionPolicy(wicket_bin="/definitely/not/a/wicket")
    with pytest.raises(FileNotFoundError):
        policy.accepts(_good_input())
