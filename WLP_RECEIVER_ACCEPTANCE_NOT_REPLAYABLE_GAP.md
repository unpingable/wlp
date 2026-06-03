# WLP_RECEIVER_ACCEPTANCE_NOT_REPLAYABLE_GAP

**Status:** candidate / non-binding. Gap note, not authorization to build.
**Filed:** 2026-06-03
**Trigger:** the receiver-gate slice (commits `9cbda96` → `f818803`)
demonstrates one lie-class — unattributed mutation claims — but does
not address the second lie-class that surfaces once a receiver
accepts: receiver acceptance is not the same object as spendable
mutation authority. A claim being admissible does not entitle the
caller to repeated effects on the basis of one admission.

## The cut

> **Admission is not consumption.**

Tighter:

> **A receiver may accept a claim without minting an infinite handle
> to mutate it.**

Tighter still, at the wire altitude this note covers:

> **Receiver acceptance is not replayable mutation authority.**

Distinct from the receiver-gate candidate's cut: the receiver-gate
note blocks *unattributed* claims from inducing mutation at all.
This note blocks *attributed and admitted* claims from inducing
mutation more than once on the basis of a single admission.

## Forcing case (visible specimen)

`examples/receiver_gate/receiver_gate.py` admits the same
`(claim, witness)` pair repeatedly within the 5-minute freshness
window:

```python
gate = ReceiverGate(policy=LocalAdmissionPolicy())
witness = make_probe_receipt("api-01", NOW)
claim = make_restart_claim("api-01",
                           witness_hash=witness["custody"]["artifact_hash"])
store = {witness["custody"]["artifact_hash"]: witness}

gate.handle(claim, store, now=NOW)  # accepted, restart_count == 1
gate.handle(claim, store, now=NOW)  # accepted, restart_count == 2
gate.handle(claim, store, now=NOW)  # accepted, restart_count == 3
```

HMAC verifies; witness target matches; admission policy accepts;
the gate mutates. The witness store has no notion of consumption;
the gate has no notion of grants. Replay-within-freshness is not a
test failure today — it is the documented behavior of the fixture.
That is the bug class this gap names.

## What WLP currently covers

WLP today carries:

- `causal_parents` and `custody.artifact_hash` for content anchoring;
- `temporal_envelope` for freshness windows;
- the receiver-gate fixture's HMAC anchor model for trust.

WLP does **not** carry:

- a single-use semantic ("this witness has been consumed");
- a grant / lease / token shape a receiver can mint upon acceptance
  and burn upon mutation;
- a nonce model that distinguishes "fresh admission" from "first
  admission";
- replay-guard structure that survives gate restart.

## Three honest forms for the spendability primitive

Listed for register discipline; none are ratified.

1. **Receiver-side grant store.** Acceptance mints a `Grant` in
   receiver-local state, keyed by `(witness_hash, claim_hash)` or
   a fresh nonce. Mutation consumes the grant. Grant store is
   receiver memory, not wire payload. Lightest: no WLP schema
   change.
2. **Witness-side consumption mark.** The witness carries a
   `single_use: true` field; the receiver records consumption in a
   local "consumed witnesses" set. Witness stays attributable;
   receiver tracks burn. Middle weight: wire surface widens by one
   advisory field, receiver state still does the work.
3. **Wire-level grant receipt.** The receiver emits a
   `GrantReceipt` upon acceptance which the caller must surrender
   alongside the claim on the mutation request. The receipt
   carries its own nonce + scope; spendability is on-camera in
   WLP wire shape. Heaviest: new wire artifact, custody/signing
   implications, SPEC §5 promotion conversation.

The choice depends on whether spendability is receiver state or
wire state — which is itself the gap.

## Do not implement until

- A forcing case beyond the receiver-gate fixture exists. The
  fixture's replay is the visible specimen; a real consumer asking
  "how do I prevent double-restart on the same probe failure?" is
  the production forcing case. Until that consumer surfaces, the
  candidate is at the "name the slot" altitude, not the "build the
  slot" altitude.
- A working note or design sketch picks among the three honest
  forms above. Building (1) without (3) is fine; building (3)
  ratifies a wire artifact and cannot be undone by changing a
  receiver's memory.
- The receiver-gate candidate's gates remain unbothered. Adding
  spendability does not relax the witness-anchor model conditions
  on `ClaimReceipt` promotion; the two gaps compose, they do not
  substitute.
- The admission engine's role stays bounded. Wicket admits, the
  receiver consumes, an accountant lives somewhere — this note
  must not be read as "Wicket also owns spendability."

## Containment

This note does not authorize:

- Adding a `single_use` / `consumed_at` / nonce field to any WLP
  receipt shape.
- Adding a grant / lease / token receipt class to SPEC.md.
- Promoting `ClaimReceipt` to load-bearing protocol status; the
  receiver-gate candidate gates that, and adding spendability does
  not change those conditions.
- Making the receiver-gate fixture's `ReceiverGate.handle` track
  consumption. The fixture's replay vulnerability is the visible
  specimen, not the venue for the implementation.
- Editing Wicket to evaluate spendability. Wicket's surface is
  admission; this gap is one altitude further out at the
  consumption boundary.

## Sibling references

- `WLP_RECEIVER_GATE_CANDIDATE.md` — names the first lie-class
  (unattributed mutation). This gap names the second
  (admitted-but-replayable mutation). Same family; different
  failure surface. The two candidates compose.
- `examples/receiver_gate/` — the visible specimen lives there.
  The replay shape above is reproducible by editing no code.
- `~/git/wicket/WICKET_REMOTE_STANDING_ADAPTER_GAP.md` — adjacent
  vocabulary boundary; same posture of naming the slot early
  without building it.
- `docs/open-issues.md` → `validation_result is not action_attestation`
  — receiver acceptance ≠ replayable mutation authority is a
  structural specialization of that distinction at the mutation
  altitude.

## Compression

> Wicket admits claims. WLP carries claims. Receivers consume
> grants. None of those are the same object.
