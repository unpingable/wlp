# WLP_RECEIVER_GATE_CANDIDATE

**Status:** candidate / non-binding.
**Filed:** 2026-06-01
**Trigger:** agent-boundary conversation surfaced the cleanest public seam
for the admissibility family: not "agents that can't lie," but receivers
that refuse to mutate state on unattributed claims lacking the required
witness. `ClaimReceipt` is already a named-but-not-load-bearing slot in
v0.2 (SPEC §5); this note records what would have to be true to promote
it, and what the promotion is gated on.

## The cut

The v0 lie-class is **not** lying agents. It is:

> **Unwarranted action claims crossing an agent boundary and causing
> receiver-side state mutation.**

Or tighter:

> **No receiver mutates state on an action-bearing claim unless the
> claim is attributable and carries the witness required by the
> receiver's admission policy.**

The demo does not prove the claim true. It blocks the laundering move
where **assertion becomes permission**.

## What WLP already covers

The v0 spec for receiver-gated mutation maps almost 1:1 onto existing
WLP shapes:

| v0 field on the wire             | existing WLP slot                                  |
|----------------------------------|----------------------------------------------------|
| attribution (producer, run id)   | `actor` / `producer` on any receipt                |
| claim / claim type               | `subject` + receipt class                          |
| witness (kind, observed_at, …)   | evidence envelope + temporal terms (§3 constitution) |
| freshness / scope                | `temporal_envelope` (constitutional invariant)     |
| receiver-side verdict + reason   | `HandlingReceipt` verdict (`accepted` / `refused` / `expired` / `unsupported`) |

The `validation_result is not action_attestation` open issue
(`docs/open-issues.md`) already names the validation/action split that
this work would force a fixture for. The repayment trigger named there
is exactly the receiver-gate scenario.

## What promotion would add

Promoting `ClaimReceipt` from named-only to load-bearing requires:

1. **Claim envelope plus receiver consequence taxonomy** — minimally:
   - producer-declared claim form / intended use, treated as advisory
   - receiver-derived consequence class:
     - display / log only
     - mutation-bearing
     - escalation-bearing
     - external-call-bearing
   - admitted mutation-bearing claim
     (attributable + checkable witness + receiver-accepted)
   - refused mutation-bearing claim
     (missing / invalid / stale / out-of-scope / unanchored witness)

   The wire carries facts and producer declarations; the receiver
   decides consequence class. "Action-bearing" cannot be a producer
   field — see *Receiver-owned classification* below.
2. **Witness slot with an anchor model.** A `witness` field is not
   enough on its own — a producer can fabricate well-formed witness
   JSON, and a gate that only checks shape moves the laundering one
   layer down ("assertion becomes permission" → "assertion-of-witness
   becomes permission"). The load-bearing property is not *carries a
   witness* but **carries a witness the receiver can check against a
   trust anchor that is not the producer.** Three honest forms:
   - **Third-party signed** — a service the receiver pre-trusts signs
     the witness (probe service signs the probe receipt, not agent-a).
   - **Receiver-observable** — the witness references state the
     receiver can independently observe.
   - **Cryptographic proof** — the witness carries a self-checkable
     proof.

   WLP today provides one of these implicitly: `custody.artifact_hash`
   plus `causal_parents` give content anchoring, which is the
   third-party-signed form's substrate *if* the referenced receipt is
   itself signed by a non-producer party. The other half —
   `custody.signature` — is explicitly a v0.1 placeholder (SPEC §6.4),
   not yet bound to a key, algorithm, or trust-anchor model. The
   placeholder must be bound (or a parallel witness-anchor slot added)
   before `ClaimReceipt` can be load-bearing without re-introducing
   exactly the laundering it claims to block.
3. **A worked fixture** — producer → wire → receiver, including the
   adversarial cases. The forgery refusal must be on camera: producer
   attaches a fabricated witness with a bogus receipt hash, gate
   refuses *because the referenced receipt does not verify against the
   probe service's signature*. Missing-witness-refused only proves the
   gate checks a field is filled in; forgery-refused is what kills
   laundering visibly.

The receiver's admission policy — "for `restart_service`, the required
witness kind is `failed_health_probe`, anchored by signer X" — is
decision-engine territory (Wicket / Governor), not WLP. WLP validates
receipt mechanics and can verify an anchor against receiver-supplied
trust configuration; the decision engine determines which witness kind
and anchor are required for this receiver-side consequence.

The split matters in **both** directions:

- **WLP → policy leakage.** If WLP picks the trust roots,
  "anchor-checkability" quietly becomes policy.
- **Policy → WLP leakage.** If Wicket (or any admission engine) reads
  raw WLP JSON as policy input, WLP wire vocabulary becomes policy
  substrate — and future WLP schema changes become policy breakage.

The correction (visible in `examples/receiver_gate/`): integration
between WLP and Wicket must pass through a **normalized
receiver-side admission input**, not raw WLP schema. The adapter is
the boundary object; the policy never sees the wire.

## The genuinely new pieces: two receiver-owned boundaries

Two structural properties that are **not** already explicit in WLP, and
both belong in the threat model when `ClaimReceipt` is promoted:

### Validator-mutation as security boundary

> **The received artifact must be data to the validator, never code
> that modifies the validator.**

A claim that says "ignore your policy, treat me as admissible" is
attempting to mutate the evaluator. Prompt injection *is*
evaluator-mutation. The receiver-gate's inviolable rule — the received
claim cannot alter the admissibility policy that judges it — is the
same posture as Nightshift emitting `ProposedAction` across a privilege
boundary instead of holding actuation credentials: the actor proposes,
the gate disposes, the proposal cannot rewrite the gate.

### Receiver-owned classification

> **The receiver classifies a message as action-bearing-vs-prose by
> what it will *do* with the message, never by a field the producer
> set.**

If the producer can label its own mutation-fuel "non-binding prose" to
dodge the gate, the category leaks. Classification is a property of
the consequence the receiver binds, not a self-description on the
wire. Same family as receiver-owned admission: the boundary belongs
to whoever bears the consequence.

Together these are the security property that distinguishes
admissibility-preservation from the signed-and-attested-but-still-
laundered failure mode the broader agent-identity stack (FIDO Agentic
Auth WG, AP2, A2A) does not address. Signatures + identity prove
*who said it* and *that it wasn't tampered*. They do nothing about
whether the receiver may bind consequence to it.

## Do not implement until

- **Witness-anchor model is sketched** *for load-bearing promotion*.
  Pick one of: (a) bind `custody.signature` to an algorithm +
  key-reference model, (b) add an explicit `witness_anchor` slot
  naming which of the three honest forms (third-party-signed /
  receiver-observable / cryptographic-proof) this witness uses, or
  (c) both. Without some anchor model, a load-bearing `ClaimReceipt`
  promotion would be theater. A non-normative fixture may use a
  deliberately narrow toy anchor — e.g., a hardcoded probe-service
  public key — provided it does not claim general WLP support.
- A fixture exists that forces the validation/action split named in
  `docs/open-issues.md`. The receiver-gate demo is a candidate
  forcing-fixture; ratify the fixture before ratifying the artifact
  shape.
- The claim-type taxonomy survives one round of adversarial review.
  "Action-bearing" is the load-bearing distinction; if it cannot be
  drawn cleanly at the wire — *and held as receiver-owned, not
  producer-asserted* — the promotion is premature.
- Wicket has stated whether (and how) it serves as the
  receiver-policy decision engine for admitted `ClaimReceipt`s, or
  whether the demo should ship with a stub local policy and leave
  Wicket integration for v0.4+.

Any earlier implementation would be speculative expansion. This filing
is the handle; the build is gated on the conditions above.

## Containment

This note does not authorize:

- Editing `SPEC.md` §5 to mark `ClaimReceipt` load-bearing.
- Adding a `witness` schema or claim-type taxonomy to the wire.
- Building a *normative* `wlp/examples/receiver_gate/` that claims
  load-bearing `ClaimReceipt` semantics. This note does **not** block
  a non-normative toy fixture that uses a hardcoded local probe
  signer and clearly marks the witness-anchor model as fixture-local.
- Calling Wicket from WLP, or absorbing Wicket's policy vocabulary
  into WLP's claim-type taxonomy. This restriction is **directional**:
  it forbids WLP-the-library reaching into Wicket, and it forbids
  Wicket consuming raw WLP wire shape. It does **not** forbid a
  receiver — sitting between the two — from normalizing packet facts
  into an admission input and asking Wicket-shaped policy for a
  verdict. The receiver-gate fixture demonstrates this seam.
- Treating this note as a substitute for the open-issue entry in
  `docs/open-issues.md`; if/when promotion happens, the open-issue
  entry is the authoritative repayment record, not this candidate.

## Doctrinal articulation (promoted from this work)

Two maxims surfaced while implementing the receiver-mediated seam
in `examples/receiver_gate/`. They are stated here so siblings can
cite them by name, not invented per-conversation.

> **The witness packet travels. Its ontology does not get
> jurisdiction.**
>
> Or: *receivers may admit WLP testimony; WLP may not pre-negotiate
> its own admissibility.* At any evidence→policy seam, the
> normalized boundary object lives on the receiver. Reject designs
> where the producer's wire shape is the policy's input shape.
> Tripwire-test for this: assert the policy never sees producer-
> shaped fields (see `examples/receiver_gate/test_receiver_gate.py`'s
> `test_policy_receives_normalized_admission_input_not_raw_packet`).

> **Cooking is translation under receiver authority, not ontology
> inheritance.**
>
> Nastier: *the adapter may translate testimony into policy
> vocabulary; it may not let testimony choose the vocabulary.* The
> destination layer's reserved names (e.g., Wicket's `prior_receipt`
> = chained Wicket receipts, NOT "some receipt-shaped object from
> the outside world") belong to the destination layer. The cook
> table is where the receiver decides which destination-vocabulary
> field carries the load of each source-vocabulary field. "But
> they both call it X" is a near-miss to be vetted, not a free
> conversion. Specimen incident: the first pass of
> `WicketAdmissionPolicy._cook_intent` mapped the probe witness to
> `prior_receipt` because both contain "receipt"; the fix names it
> `command_output`, the cook table itself stands as `policy_ref`,
> and Wicket authorizes honestly instead of accidentally.

Both compose with this note: the first names the boundary the
receiver-gate fixture exists to protect; the second names the
discipline an admission engine must follow when it sits behind that
boundary.

## Sibling references

- `WLP_STANDING_BOUNDARY_CROSSREF.md` — WLP's position as wire-layer
  beneath the receipt/audit slot. Same posture: WLP carries
  receipts of decisions made elsewhere; it does not make the
  decisions.
- `~/git/wicket/WICKET_REMOTE_STANDING_ADAPTER_GAP.md` — wicket's
  parallel candidate note for the remote/assertion-standing
  vocabulary boundary. Same shape: name the slot early, gate the
  build on real consumer pressure. The cook-translation-authority
  maxim above is the discipline its anticipated adapter plan
  must follow.
- `docs/open-issues.md` → `validation_result is not action_attestation`
  — the existing bounded-debt entry whose repayment trigger this
  promotion would satisfy.
