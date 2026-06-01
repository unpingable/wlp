# Receiver-Gated Mutation for Witnessed Action Claims

**Status:** fixture-local example. Non-normative. Not a SPEC promotion.

This example demonstrates one killed lie-class: a receiver must not
mutate state from an unattributed action-bearing claim lacking an
anchored, fresh witness.

It is **fixture-local**. It uses one toy trust anchor — a hardcoded
HMAC-SHA256 key representing a trusted probe service. It does **not**
promote `ClaimReceipt`, define WLP's general signature model, or add
Wicket policy semantics. See `WLP_RECEIVER_GATE_CANDIDATE.md` in the
repo root for the candidate doctrine note this fixture exercises.

## The killed lie-class

> Unwarranted action claims crossing an agent boundary and causing
> receiver-side state mutation.

Tighter:

> No receiver mutates state on an action-bearing claim unless the
> claim is attributable and carries a witness the receiver can check
> against a trust anchor independent of the producer.

## Shape

```
producer agent          probe service              receiver gate
─────────────           ─────────────              ─────────────
restart_service ──────► (does not call) ──────►   classify: mutation-bearing
                                                  require: failed_health_probe
                                                           anchored by probe-service

                        observe target           ◄──── verify HMAC
                        sign witness ────────────► witness store
                                                  check freshness
                                                  mutate state iff accepted
                                                  emit HandlingReceipt-like verdict
```

Key boundaries:

- **Receiver owns classification.** `restart_service` is mutation-bearing
  because the receiver would mutate state — not because the producer
  said so. A producer-set `"non_binding": true` does not bypass this.
- **Witness anchored at a non-producer.** The probe service holds the
  HMAC key; the producer cannot forge a probe receipt. Without this,
  laundering just moves down one layer.
- **Mutation only after accepted verdict.** `refused` / `expired` /
  `unsupported` never mutate state.
- **Claim is data, not code.** Prompt-injection-shaped text in the
  claim body does not bypass the gate. The validator never executes
  what it receives.

## What this is not

- WLP's general signature model — `custody.signature` is a v0.1
  placeholder (SPEC §6.4). HMAC is fixture-local, not the eventual
  WLP crypto.
- A promotion of `ClaimReceipt` to load-bearing protocol status.
- A Wicket integration. The receiver policy is a stub local dict:
  "for `restart_service`, the required witness kind is
  `failed_health_probe`, produced by `probe-service`." Wicket may
  later replace the stub policy.
- A normative envelope schema. The dicts here have WLP-flavored
  field names but do not conform to or extend `SPEC.md`.

## Run

```bash
cd examples/receiver_gate
python3 -m pytest .
```

Tests (one per lie-class case):

- `admitted_restart_mutates_state`
- `naked_claim_refused_no_mutation`
- `missing_witness_refused_no_mutation`
- `forged_witness_refused_no_mutation`  ← the on-camera kill
- `stale_witness_expired_no_mutation`
- `producer_nonbinding_label_does_not_bypass_receiver_classification`
- `prompt_injection_cannot_modify_policy`

## Wicket integration, later

When Wicket grows a callable admission-policy surface, replace the
stub dict in `receiver_gate.py` with a Wicket call:

```
policy.accepts(
    claim_type="restart_service",
    witness_kind="failed_health_probe",
    witness_anchor="probe-service",
    target=...,
    now=...,
) -> accepted | refused | needs_evidence
```

Until then, this example is WLP-side only: a Python fixture showing
receiver-gated mutation over WLP-shaped receipts with a toy local
policy seam.
