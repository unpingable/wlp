# WLP_STANDING_BOUNDARY_CROSSREF

**Status:** cross-reference / non-binding.
**Filed:** 2026-05-28
**Trigger:** Wicket-Claude surfaced a layer-vs-component question while
filing its own `WICKET_REMOTE_STANDING_ADAPTER_GAP.md` against the
cross-constellation remote-standing doctrine. WLP needed an in-repo
statement of where it sits, so a WLP-only reader doesn't have to know
the cartography venue exists.

## The keepers

> **WLP is the wire discipline for admissible receipts, not the standing
> discipline that makes receipts admissible.**

> **WLP sits below the receipt/audit slot; it is not the audit layer itself.**

## What this note is

A pointer, not the doctrine. The doctrine filing is
`~/git/cartography/coordination/nq-REMOTE_STANDING_BOUNDARY.md`
(placeholder filing from `notquery`-Claude, 2026-05-27), with a
constellation-side cross-reference at
`~/git/cartography/coordination/wlp-notes-as-wire-layer-for-standing-boundary.md`.
Cartography is ARCHIVED (2026-06-14; committed 2026-07-13 — absorbed by
agent_gov), so "awaiting cartographer curation" is superseded: curation is
tracked at `agent_gov/working/cartography-intake-candidates-2026-06-14.md`,
and the live topology index is `agent_gov/docs/CONSTELLATION_MAP.md`.
The archived filing remains citable as history.

This file explains, inside WLP itself, how WLP relates to that doctrine.

## Position

The doctrine names five layers a remote-surface design must distinguish:

```
identity      — who/what is calling?
authz         — what verbs may this caller invoke?
standing      — what kind of testimony/request may this caller introduce?
transport     — what protects the call in flight?
receipt/audit — what durable record survives the call?
```

WLP is the wire-format-and-validation layer **beneath** the receipt/audit
slot. The standing-bearing components (Standing-the-tool, NQ, Wicket,
Nightshift, AG) decide / refuse / qualify / handle. WLP records their
decisions as portable receipt-shaped testimony.

```
Standing / NQ / Wicket / Nightshift / AG
  decide / refuse / qualify / handle
        ↓
WLP
  records the decision as portable receipt-shaped testimony
        ↓
adopter
  storage, discovery, UX, audit aggregation
```

WLP is not in the same row as the per-component manifestations. It is
the layer those manifestations serialize into.

## Coverage against the doctrine's deferred questions

The doctrine names five questions deferred ("What this doctrine does not
yet specify"). WLP's coverage:

| # | Question                                                | WLP coverage                                                                                                                                                                                                              |
|---|----------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1 | Wire format for `StandingRequest` / `StandingDecision`   | **Partial.** `AuthorizationReceipt` defines the emission shape — the artifact a `StandingDecision` serializes into. WLP does not define the resolver-interaction protocol itself; that is Standing-the-tool's territory. |
| 2 | Cross-component receipt provenance format                | **Materially answered.** `custody.causal_parents` (refs by `artifact_hash`, SPEC §6.4) plus v0.2 graph-aware `handle(parent, context, opts)`. The v0.2 shape carries each canonical chain on its own surface — NQ findings → Nightshift posture (the forward channel from the NQ ↔ NS channel split); policy → Wicket admissibility → action (the Wicket preflight chain) — without forcing distinct flows into one serial pipeline. |
| 3 | Revocation propagation semantics                         | **Partial.** v0.2 `RevocationReceipt` defines artifact semantics: changes present standing, never erases historical validity, fail-closed in the revocation direction, non-recursive in v0.2. Runtime *propagation* — how downstream consumers that already admitted testimony find out and respond — is outside WLP's scope by design. |
| 4 | Audit-aggregation surface                                | **Not answered, by design.** Per `docs/open-issues.md`: WLP punts workflow, discovery, storage, and UX to adopters.                                                                                                        |
| 5 | Standing-tool config vocabulary                          | **Slot only.** `policy_refs` and standing class are open-ended slots; Standing-the-tool populates the vocabulary.                                                                                                          |

## What WLP refuses, in this context

- WLP is not a `StandingResolver`. It does not decide whether a caller has
  standing; it carries the receipt of whoever did.
- WLP is not an audit aggregator. It validates one artifact at a time.
  The storage shape, discovery shape, and UX of an audit surface belong
  to adopters (see `docs/open-issues.md`).
- WLP is not a court. The constitution is "every WLP artifact must carry
  the terms under which it stops binding," not "WLP decides when the
  terms are met." That is a domain decision the standing-bearing
  component makes before emitting the artifact.
- WLP may carry the receipt of an external reconciler, but WLP is not
  the reconciler for self-subject findings. The cross-component pattern
  (`~/git/cartography/coordination/SELF-SUBJECT-COLLAPSE.md`) names three
  forcing instances (NS, NQ-on-NQ, agent_gov); WLP is not among them and
  is not a candidate adjudicator for them.
- WLP is not a per-component manifestation of the remote-standing
  boundary. The doctrine's per-component list (NQ, Nightshift, Wicket,
  Standing-the-tool, AG) is the row of components that decide things.
  WLP is the layer their decisions serialize into. Adding WLP to that
  row would be a category error.

## Forward pressure (not yet ratified)

When Standing-the-tool grows, the natural shape is:

```
StandingResolver.assess(StandingRequest) -> StandingDecision
StandingDecision serializes as a WLP AuthorizationReceipt
  carrying standing class, scope, policy_refs, temporal_envelope, custody.
```

That is the convergence path. WLP does not need to do anything to prepare
for it; the v0.2 artifact shape already accommodates it.

## Containment

This note does not authorize:

- Defining a `StandingRequest` / `StandingDecision` wire format inside WLP.
- Adding an audit-aggregation surface to WLP.
- Calling Standing-the-tool, NQ, Wicket, or Nightshift from WLP.
- Editing `SPEC.md` to absorb remote-standing vocabulary.

WLP stays the wire layer. The doctrine's archived filing stays in
cartography (history); its live custody is with agent_gov. This file
just makes the relationship readable from inside WLP.
