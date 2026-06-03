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
- A normative WLP/Wicket integration product. The seam is
  fixture-local. `LocalAdmissionPolicy` (in `admission.py`) is a
  Wicket-shaped stand-in usable without the Wicket binary;
  `WicketAdmissionPolicy` (in `wicket_policy.py`) is a real bridge
  that shells out to the `wicket check` CLI when the binary is
  available. Both implement the same `AdmissionPolicy` protocol;
  the receiver gate does not know which is wired in.
- A normative envelope schema. The dicts here have WLP-flavored
  field names but do not conform to or extend `SPEC.md`.

## Run

```bash
cd examples/receiver_gate
python3 -m pytest .
```

Tests (`test_receiver_gate.py`, one per lie-class case plus the
receiver-mediated boundary):

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

Wicket wiring tests (`test_wicket_policy.py`, skip-on-missing-binary
for the live invocations):

- `wicket_policy_accepts_only_admission_input`
- `supported_restart_with_valid_witness_is_permitted`  *(needs wicket)*
- `unsupported_claim_type_is_unsupported_without_wicket`
- `wrong_witness_kind_is_refused_without_wicket`
- `wrong_witness_anchor_is_refused_without_wicket`
- `wicket_denial_reason_survives_into_admission_verdict`  *(needs wicket)*
- `wlp_crate_has_no_wicket_dependency`
- `receiver_gate_with_wicket_policy_end_to_end`  *(needs wicket)*
- `cook_table_is_the_only_admission_to_wicket_mapping`
- `missing_wicket_binary_raises_file_not_found`

Cook-seam generality tests (`test_cook_seam_generality.py`, verifies
the seam tolerates ≥2 cook-table entries without per-entry code
paths or vocabulary leakage):

- `cook_tables_share_the_same_claim_type_keys`
- `cook_tables_agree_on_required_witness_combinations`
- `local_admits_flush_cache_when_all_fields_match`
- `local_refuses_flush_cache_with_wrong_witness_{kind,anchor}`
- `local_still_admits_restart_service`
- `wicket_refuses_flush_cache_with_wrong_witness_{kind,anchor}_without_invoking`
- `wicket_admits_flush_cache_when_cooked_through_real_wicket`  *(needs wicket)*
- `wicket_still_admits_restart_service_end_to_end`  *(needs wicket)*
- `cooked_intent_for_flush_cache_has_no_wlp_wire_fields`
- `cooked_intent_carries_recipe_specific_rule_text`
- `receiver_gate_handle_is_policy_agnostic_at_source_level`
- `receiver_gate_routes_arbitrary_claim_type_through_policy`
- `receiver_gate_hmac_fixture_remains_single_anchor`  *(pins the
  single-anchor finding below)*

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

Two `AdmissionPolicy` implementations are provided:

- **`LocalAdmissionPolicy`** (`admission.py`) — a Wicket-shaped
  Python stand-in. Encodes the policy a real Wicket bridge would
  compute, but is not the kernel. Default for the unit tests; no
  external dependency.
- **`WicketAdmissionPolicy`** (`wicket_policy.py`) — the real
  bridge. Cooks `AdmissionInput` into a Wicket `Intent` JSON,
  shells out to the `wicket check` CLI, translates the returned
  `Outcome` back into an `AdmissionVerdict`. Locates the binary
  via the `WICKET_BIN` env var, common build paths, or `PATH`. The
  cook is the second adapter in the chain: WLP packet →
  `AdmissionInput` (receiver adapter) → Wicket `Intent` (cook).
  Wicket-binary-dependent tests are skipped gracefully when no
  binary is found.

The receiver gate accepts either via its `policy=` constructor
argument; both satisfy the same protocol and the gate does not know
which is wired in.

### Refusal layers in `WicketAdmissionPolicy`

```
AdmissionInput
  │
  ▼ cook table lookup
  │   miss → AdmissionVerdict("unsupported", "unsupported claim type")
  │
  ▼ witness kind/anchor precondition
  │   mismatch → AdmissionVerdict("refused", "<reason>")
  │
  ▼ cook → Wicket Intent JSON
  │
  ▼ subprocess: `wicket check`
  │
  ▼ translate Outcome.surface_verdict
      authorized      → AdmissionVerdict("accepted", "wicket authorized ...")
      denied/gap/...  → AdmissionVerdict("refused",  "wicket <verdict> (REASON_CODES)")
```

Wicket's role is the standing × precedence × scope × revocation
check given the cooked Intent. The cook table's role is the
receiver-side semantic check ("does this combination of claim_type,
witness_kind, witness_anchor map to a Wicket rule I am willing to
cite?"). Neither role overlaps; neither is delegated across the
boundary.

### Cook table

| claim_type        | required witness_kind   | required witness_anchor | Wicket evidence kind |
|-------------------|-------------------------|-------------------------|----------------------|
| `restart_service` | `failed_health_probe`   | `probe-service`         | `command_output`     |
| `flush_cache`     | `cache_pressure_signal` | `metrics-service`       | `command_output`     |

Both entries pass through the same `accepts()` code path; the only
per-claim_type knowledge is the table lookup. Adding a third entry
is a table edit, not a code change.

## Finding: HMAC fixture is single-anchor

Adding `flush_cache` to the cook table generalized the **seam**
cleanly — both `LocalAdmissionPolicy` and `WicketAdmissionPolicy`
admit it without any per-claim-type branch in `accepts()`, and the
cooked Wicket Intent carries no WLP wire vocabulary.

The receiver-gate's **HMAC verification** does not generalize at
the same altitude. `verify_probe_receipt` is hardcoded to a single
trust anchor (`TRUSTED_PROBE_ID = "probe-service"`,
`TRUSTED_PROBE_KEY = b"..."`). A `flush_cache` claim with a
witness signed by `metrics-service` would refuse at the
trust-anchor verification step, because the gate has no
metrics-service key.

This is **anchor-config, not seam-shape**. Generalizing the gate
to verify multiple anchors would mean replacing the two module-
level constants with a trust-anchor table (`anchor_id → key`) on
the gate at construction. That is a separate slice with its own
scope (key rotation, anchor authentication, fixture-vs-production
boundary) — distinct from the cook seam, which is unchanged.

The single-anchor limitation is pinned by
`test_receiver_gate_hmac_fixture_remains_single_anchor`: if the
gate later grows a trust-anchor table, that test should be updated
and end-to-end flush_cache coverage added through the gate.
