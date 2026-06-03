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
- A live Wicket integration. The admission policy is a fixture-local
  Wicket-shaped stand-in (`LocalAdmissionPolicy` in `admission.py`),
  not a bridge to the real Wicket kernel. A real deployment would
  back the same `AdmissionPolicy` protocol with a Wicket call (e.g.,
  shell out to `wicket check` over a cooked Intent).
- A normative envelope schema. The dicts here have WLP-flavored
  field names but do not conform to or extend `SPEC.md`.

## Run

```bash
cd examples/receiver_gate
python3 -m pytest .
```

Tests (one per lie-class case, plus the receiver-mediated boundary):

- `admitted_restart_mutates_state`
- `naked_claim_refused_no_mutation`
- `missing_witness_refused_no_mutation`
- `forged_witness_refused_no_mutation`  ← the on-camera kill
- `stale_witness_expired_no_mutation`
- `producer_nonbinding_label_does_not_bypass_receiver_classification`
- `prompt_injection_cannot_modify_policy`
- `unknown_claim_type_unsupported_via_policy`
- `wrong_witness_kind_refused_by_policy`
- `policy_receives_normalized_admission_input_not_raw_packet`
- `adapter_produces_admission_input_shape`
- `admission_module_has_no_wlp_coupling`

## Wicket integration: the receiver-mediated seam

This fixture demonstrates the **receiver-mediated** Wicket/WLP seam —
the only shape integration may take.

```
WLP packet (claim + witness)
        │
        ▼  receiver-side packet integrity:
           producer, witness presence, anchor
           authenticity (HMAC), claim/witness
           target consistency, freshness
        │
        ▼  adapt_packet_to_admission_input(claim, witness, now)
                 │
                 ▼  AdmissionInput { claim_type, witness_kind,
                                     witness_anchor, target, now }
                       │
                       ▼  policy.accepts(admission_input)
                       │      → AdmissionVerdict
                       │        (accepted | refused | unsupported)
                       │
        ▼  receiver acts on verdict (mutate iff accepted)
        ▼  emit HandlingReceipt
```

The forbidden shapes:

- WLP calling Wicket directly. WLP emits packets; the receiver
  couples to admission.
- Wicket parsing raw WLP JSON. The policy receives `AdmissionInput`
  only. The adapter is the boundary object — and the tests
  `policy_receives_normalized_admission_input_not_raw_packet` and
  `admission_module_has_no_wlp_coupling` enforce this in code.
- WLP absorbing Wicket policy vocabulary (claim-type taxonomy stays
  WLP-side; admissibility-policy vocabulary stays admission-side).

The fixture's `LocalAdmissionPolicy` is a Wicket-shaped stand-in: it
encodes the policy a real Wicket bridge would compute, but it is
not the kernel. To swap in real Wicket, implement the
`AdmissionPolicy` protocol by translating `AdmissionInput` into a
cooked Wicket `Intent` and shelling out to `wicket check` (or an
equivalent FFI). The receiver gate is unchanged by that swap.
