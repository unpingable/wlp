from __future__ import annotations

import copy
import dataclasses
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal


Verdict = Literal["accepted", "refused", "expired", "unsupported"]

TRUSTED_PROBE_ID = "probe-service"
TRUSTED_PROBE_KEY = b"fixture-local-probe-key-not-a-wlp-crypto-model"
MAX_WITNESS_AGE = timedelta(minutes=5)


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def artifact_hash(value: dict[str, Any]) -> str:
    unsigned = copy.deepcopy(value)
    custody = unsigned.get("custody")
    if isinstance(custody, dict):
        custody.pop("signature", None)
        custody.pop("artifact_hash", None)
    return hashlib.sha256(canonical_json(unsigned)).hexdigest()


def sign_probe_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    signed = copy.deepcopy(receipt)
    signed.setdefault("custody", {})
    signed["custody"].pop("signature", None)
    signed["custody"].pop("artifact_hash", None)
    digest = artifact_hash(signed)
    signature = hmac.new(TRUSTED_PROBE_KEY, digest.encode(), hashlib.sha256).hexdigest()
    signed["custody"]["artifact_hash"] = digest
    signed["custody"]["signature"] = signature
    return signed


def verify_probe_receipt(receipt: dict[str, Any]) -> bool:
    custody = receipt.get("custody", {})
    claimed_hash = custody.get("artifact_hash")
    claimed_sig = custody.get("signature")
    if not claimed_hash or not claimed_sig:
        return False

    actual_hash = artifact_hash(receipt)
    if not hmac.compare_digest(claimed_hash, actual_hash):
        return False

    expected = hmac.new(TRUSTED_PROBE_KEY, actual_hash.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(claimed_sig, expected)


@dataclasses.dataclass(frozen=True)
class HandlingReceipt:
    verdict: Verdict
    reason: str
    mutated: bool = False


class ReceiverGate:
    def __init__(self) -> None:
        self.restart_count = 0

    def handle(
        self,
        claim: dict[str, Any],
        witness_store: dict[str, dict[str, Any]],
        now: datetime,
    ) -> HandlingReceipt:
        claim_type = claim.get("subject", {}).get("claim_type")
        target = claim.get("subject", {}).get("target")

        # Receiver-owned classification. Producer labels are advisory only.
        if claim_type != "restart_service":
            return HandlingReceipt("unsupported", "unsupported claim type")

        if not claim.get("producer"):
            return HandlingReceipt("refused", "missing producer attribution")

        witness_hash = claim.get("witness_ref", {}).get("artifact_hash")
        if not witness_hash:
            return HandlingReceipt("refused", "missing required witness")

        witness = witness_store.get(witness_hash)
        if witness is None:
            return HandlingReceipt("refused", "referenced witness not found")

        if witness.get("producer") != TRUSTED_PROBE_ID:
            return HandlingReceipt("refused", "witness producer is not trusted probe service")

        if not verify_probe_receipt(witness):
            return HandlingReceipt("refused", "witness failed trust-anchor verification")

        subject = witness.get("subject", {})
        if subject.get("kind") != "failed_health_probe":
            return HandlingReceipt("refused", "wrong witness kind")

        if subject.get("target") != target:
            return HandlingReceipt("refused", "witness target does not match claim target")

        observed_at_raw = witness.get("observed_at")
        try:
            observed_at = datetime.fromisoformat(observed_at_raw)
        except (TypeError, ValueError):
            return HandlingReceipt("refused", "invalid witness observed_at")

        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)

        if now - observed_at > MAX_WITNESS_AGE:
            return HandlingReceipt("expired", "witness expired")

        self.restart_count += 1
        return HandlingReceipt("accepted", "mutation admitted by receiver policy", mutated=True)


def make_probe_receipt(target: str, observed_at: datetime) -> dict[str, Any]:
    return sign_probe_receipt({
        "receipt_class": "ProbeReceipt",
        "producer": TRUSTED_PROBE_ID,
        "subject": {
            "kind": "failed_health_probe",
            "target": target,
        },
        "observed_at": observed_at.isoformat(),
        "result": {
            "status": "failed",
        },
        "custody": {},
    })


def make_restart_claim(
    target: str,
    producer: str = "agent-a",
    witness_hash: str | None = None,
    non_binding: bool = False,
    text: str = "restart service because health probe failed",
) -> dict[str, Any]:
    claim: dict[str, Any] = {
        "receipt_class": "ClaimReceipt",
        "producer": producer,
        "subject": {
            "claim_type": "restart_service",
            "target": target,
        },
        "text": text,
        "producer_declared_non_binding": non_binding,
    }
    if witness_hash is not None:
        claim["witness_ref"] = {"artifact_hash": witness_hash}
    return claim
