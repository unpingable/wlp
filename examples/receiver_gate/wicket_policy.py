"""Wicket-backed AdmissionPolicy for the receiver gate.

This module is the real wiring of the receiver-mediated seam: a concrete
`AdmissionPolicy` implementation that translates `AdmissionInput` into a
Wicket `Intent`, shells out to the `wicket` CLI, and translates the
returned `Outcome` back into an `AdmissionVerdict`.

Doctrinal invariants (mirroring `admission.py`):

- Wicket never sees raw WLP wire shape. The cook here consumes only
  `AdmissionInput` and produces a Wicket Intent JSON. Field names on
  the Wicket side are Wicket's, not WLP's.
- WLP does not call Wicket. The receiver gate (a receiver-side
  fixture) couples to admission; the WLP crate has no dependency on
  Wicket.
- The cook table is a receiver-side configuration: it names which
  Wicket rule corresponds to which WLP claim_type, and which witness
  combinations the receiver is willing to cook into an Intent at all.
  Wicket's role is the standing/precedence/scope/revocation check
  given the cooked Intent.

Refusal order:

1. Cook table miss → `unsupported`. The receiver does not know how
   to map this claim_type to a Wicket rule. (Wicket has no opinion
   on unknown actions.)
2. Witness kind/anchor mismatch → `refused`. The cook table entry's
   structural precondition is not met. (Wicket's `EvidenceKind` is
   `prior_receipt`/`tool_output`/..., not `failed_health_probe`, so
   this semantic check belongs in the cook.)
3. Wicket invocation → translate the surface verdict.

A real deployment might replace the subprocess invocation with an
in-process FFI binding; the seam (`accepts(AdmissionInput) ->
AdmissionVerdict`) is what matters, not the transport.
"""
from __future__ import annotations

import dataclasses
import json
import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from admission import AdmissionInput, AdmissionVerdict


WICKET_INTENT_TTL = timedelta(minutes=5)


@dataclasses.dataclass(frozen=True)
class _CookRecipe:
    """One entry in the cook table.

    Names the Wicket-side rule and Intent template that the receiver
    chooses for a given claim_type, plus the witness combination the
    receiver is willing to forward into Wicket at all.
    """

    required_witness_kind: str
    required_witness_anchor: str
    intended_action: str
    operation_class: str
    rule_text: str
    expected_effect_template: str  # uses `{target}`


DEFAULT_COOK_TABLE: dict[str, _CookRecipe] = {
    "restart_service": _CookRecipe(
        required_witness_kind="failed_health_probe",
        required_witness_anchor="probe-service",
        intended_action="restart_service",
        operation_class="execute",
        rule_text=(
            "restart_service is authorized by a failed_health_probe witness "
            "anchored at probe-service"
        ),
        expected_effect_template="restart {target}",
    ),
}


def find_wicket_binary() -> str | None:
    """Locate a `wicket` binary using `WICKET_BIN`, common build paths,
    and PATH. Returns None if no usable binary is found."""
    env = os.environ.get("WICKET_BIN")
    if env and Path(env).is_file() and os.access(env, os.X_OK):
        return env
    home = Path.home()
    for candidate in (
        home / "git" / "wicket" / "target" / "release" / "wicket",
        home / "git" / "wicket" / "target" / "debug" / "wicket",
    ):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    which = shutil.which("wicket")
    return which


class WicketAdmissionPolicy:
    """Wicket-backed implementation of the `AdmissionPolicy` Protocol.

    Construction does not require the binary to exist; `accepts()` does.
    A binary path may be provided explicitly; if omitted, the discovery
    helper is used. If the binary is not found, `accepts()` raises
    `FileNotFoundError`, which callers may catch (or skip in tests).

    The `gate_standing` knob configures what standing the receiver
    claims for itself when cooking the Intent — typically `execute`
    for a real gate. Tests can lower it to `recommend` to exercise
    Wicket's denial path.
    """

    def __init__(
        self,
        wicket_bin: str | None = None,
        *,
        cook_table: dict[str, _CookRecipe] | None = None,
        actor: str = "wlp-receiver-gate",
        gate_standing: str = "execute",
        timeout_sec: float = 5.0,
    ) -> None:
        self._wicket_bin = wicket_bin
        self._cook_table = dict(cook_table) if cook_table else dict(DEFAULT_COOK_TABLE)
        self._actor = actor
        self._gate_standing = gate_standing
        self._timeout_sec = timeout_sec

    # ---- AdmissionPolicy.accepts ---------------------------------------------

    def accepts(self, admission_input: AdmissionInput) -> AdmissionVerdict:
        recipe = self._cook_table.get(admission_input.claim_type or "")
        if recipe is None:
            return AdmissionVerdict("unsupported", "unsupported claim type")
        if admission_input.witness_kind != recipe.required_witness_kind:
            return AdmissionVerdict(
                "refused",
                f"witness kind {admission_input.witness_kind!r} does not "
                "satisfy admission policy",
            )
        if admission_input.witness_anchor != recipe.required_witness_anchor:
            return AdmissionVerdict(
                "refused",
                f"witness anchor {admission_input.witness_anchor!r} does "
                "not satisfy admission policy",
            )

        intent = self._cook_intent(admission_input, recipe)
        outcome = self._invoke_wicket(intent)
        return self._translate(outcome)

    # ---- Cook ----------------------------------------------------------------

    def _cook_intent(
        self, admission_input: AdmissionInput, recipe: _CookRecipe
    ) -> dict[str, Any]:
        """Translate normalized admission facts into a Wicket Intent.

        This is the receiver-side cook layer — the analog of Wicket's
        own `cook.rs` for verb packets, but for admission inputs. It
        is the second adapter in the chain: WLP packet → AdmissionInput
        (receiver adapter) → Wicket Intent (this cook).

        Evidence shape, for an `execute`-class operation Wicket needs
        both a basis kind (`policy_ref` or `human_confirmation`) and a
        trace kind (`tool_trace` / `test_log` / `command_output` /
        `file_hash`). The cook supplies:

          - PolicyRef: the receiver's own admission policy entry —
            the cook table itself is the receiver's policy, and the
            rule_text quotes its substance.
          - CommandOutput: the WLP witness. In Wicket's vocabulary a
            probe receipt is honestly a "command output" (a tool was
            run, here is its result), not a prior receipt — Wicket's
            `prior_receipt` is for chained Wicket receipts.
        """
        now = admission_input.now
        target = admission_input.target or ""
        valid_from = _iso(now - WICKET_INTENT_TTL)
        valid_until = _iso(now + WICKET_INTENT_TTL)
        policy_ref = {
            "ref": f"wlp://receiver-gate/cook-table#{recipe.intended_action}",
            "kind": "policy_ref",
            "issuer": "receiver-gate-policy",
            "subject": target,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "status": "valid",
        }
        witness_ref = {
            "ref": (
                f"wlp://witness/{recipe.required_witness_kind}"
                f"@{recipe.required_witness_anchor}/{target}"
            ),
            "kind": "command_output",
            "issuer": recipe.required_witness_anchor,
            "subject": target,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "status": "valid",
        }
        return {
            "actor": self._actor,
            "actor_standing": {
                "class": self._gate_standing,
                "provenance": "caller_asserted",
            },
            "intended_action": recipe.intended_action,
            "operation_class": recipe.operation_class,
            "target": target,
            "scope_assertion": {
                "scope_includes_target": True,
                "provenance": "caller_asserted",
                "evidence_refs": [f"wlp://receiver-gate/scope/{target}"],
            },
            "claimed_basis": {
                "rule": recipe.rule_text,
                "evidence_refs": [policy_ref, witness_ref],
            },
            "precedence": {
                "resolution": "active",
                "provenance": "caller_asserted",
                "evidence_refs": [],
            },
            "revocation": {
                "basis_revoked": False,
                "standing_forbidden": False,
                "provenance": "caller_asserted",
                "evidence_refs": [],
            },
            "expected_effect": recipe.expected_effect_template.format(target=target),
            "call_timestamp": _iso(now),
        }

    # ---- Invoke --------------------------------------------------------------

    def _invoke_wicket(self, intent: dict[str, Any]) -> dict[str, Any]:
        binary = self._wicket_bin or find_wicket_binary()
        if not binary:
            raise FileNotFoundError(
                "wicket binary not found; set WICKET_BIN, build wicket, "
                "or pass wicket_bin explicitly"
            )
        result = subprocess.run(
            [binary, "check"],
            input=json.dumps(intent).encode(),
            capture_output=True,
            timeout=self._timeout_sec,
            check=False,
        )
        if result.returncode not in (0, 2):
            raise RuntimeError(
                f"wicket exited {result.returncode}: "
                f"{result.stderr.decode(errors='replace')}"
            )
        try:
            return json.loads(result.stdout.decode())
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"wicket produced non-JSON output: {result.stdout!r}"
            ) from exc

    # ---- Translate -----------------------------------------------------------

    def _translate(self, outcome: dict[str, Any]) -> AdmissionVerdict:
        verdict = outcome.get("surface_verdict")
        salient = _salient_reason_codes(outcome)
        suffix = f" ({', '.join(salient)})" if salient else ""
        if verdict == "authorized":
            return AdmissionVerdict("accepted", f"wicket authorized{suffix}")
        if verdict == "advisory_only":
            return AdmissionVerdict(
                "refused", f"wicket returned advisory_only{suffix}"
            )
        if verdict == "denied":
            return AdmissionVerdict("refused", f"wicket denied{suffix}")
        if verdict == "gap":
            return AdmissionVerdict("refused", f"wicket gap{suffix}")
        if verdict == "unaccounted":
            return AdmissionVerdict("refused", f"wicket unaccounted{suffix}")
        return AdmissionVerdict(
            "refused", f"wicket emitted unknown surface_verdict {verdict!r}"
        )


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _iso(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


_NOISE_SUFFIXES = ("_CALLER_ASSERTED_UNVERIFIED", "_LADDER_V1_FLAT")


def _salient_reason_codes(outcome: dict[str, Any]) -> list[str]:
    """Pick the salient non-OK reason codes from a Wicket outcome.

    Mirrors the brief-print filter in wicket's main.rs so the
    `AdmissionVerdict.reason` carries Wicket's substantive verdict
    explanation without the caller-asserted-unverified noise.
    """
    codes = outcome.get("reason_codes", []) or []
    out: list[str] = []
    for c in codes:
        if not isinstance(c, str):
            continue
        if any(c.endswith(suffix) for suffix in _NOISE_SUFFIXES):
            continue
        if c.endswith("_OK"):
            continue
        if c not in out:
            out.append(c)
    return out[:3]
