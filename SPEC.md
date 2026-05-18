# WLP v0.1 Specification

## 1. Scope

WLP is a wire protocol for preserving admissibility across system boundaries.

WLP is **domain-semantically neutral**: it does not know what a patient,
ticket, invoice, incident, pull request, pallet, or moderation event means.

WLP is **admissibility-semantically opinionated**: it has strong opinions
about standing, scope, evidence, time, revocation, and contestability — the
structural properties that determine whether an artifact retains authority
after crossing a system boundary.

WLP **validates artifacts**. It does **not** decide whether the world should
have produced them. Decisions about whether an underlying act is admissible
belong upstream — in a decision engine such as Wicket or Governor — not in
WLP.

## 2. What WLP is not

- an ontology
- a workflow engine
- a policy evaluator
- an agent protocol
- a daemon
- a trust layer
- a ledger product
- a decision engine
- a replacement for any local domain schema

## 3. Constitution

> **Every WLP artifact must carry the terms under which it stops binding.**

A WLP artifact without a parseable temporal envelope is invalid. A WLP
artifact whose envelope has elapsed has no standing. A WLP artifact whose
policy reference cannot be supported must not be silently accepted.

## 4. Design rule

> **WLP should make laundering harder than refusal.**

Any consumer that loses scope, evidence, custody, or temporal information
while handling a WLP artifact must emit a HandlingReceipt that surfaces
the loss as degradation or refusal — never as silent acceptance.

## 5. Artifact classes

| Class                  | Role                                                                                            |
| ---------------------- | ----------------------------------------------------------------------------------------------- |
| `ClaimReceipt`         | A party asserts a statement about a subject.                                                    |
| `AuthorizationReceipt` | An actor is authorized to perform an operation, under stated terms.                             |
| `HandlingReceipt`      | A consumer records what it did (or refused) with a parent artifact.                             |
| `RevocationReceipt`    | A previously-issued artifact's present standing is mutated; historical validity is unaffected.  |
| `ContestReceipt`       | A previously-issued artifact is challenged on stated grounds.                                   |

`AuthorizationReceipt`, `HandlingReceipt`, and `RevocationReceipt` are
load-bearing in v0.2. `ClaimReceipt` and `ContestReceipt` remain named so
that the wire grammar reserves them; their detailed semantics will be
ratified by later fixtures.

### 5.1 RevocationReceipt

A `RevocationReceipt` mutates the **present standing** of a previously-issued
artifact. It does **not** invalidate the historical artifact; it changes how
a consumer must evaluate the targeted artifact going forward.

**Invariant.** *RevocationReceipt does not invalidate the targeted artifact.
It changes the targeted artifact's current standing. Historical validity is
unaffected.*

**Targeting.** `transition.target` carries the canonical hash of the revoked
artifact, where:

```
parent_hash = sha256(canonical_json(parent_artifact))
```

This is the hash defined in §9 — the artifact-as-serialized hash. Not the
receipt hash, not an evaluation-output hash, not any context-dependent hash.
`transition.operation` should be `"revoke"`.

**Admissibility of the revocation itself.** A `RevocationReceipt` is subject
to the same admissibility checks as any other WLP artifact: temporal envelope
must be valid (not expired, not future-dated); `policy_refs` must be
non-empty and cite policy schemes the consumer supports. An inadmissible
revocation does not bind, and produces no mutation of the targeted artifact's
standing. "Fail-closed" for a revocation means *the revocation does not
bind* — it does **not** mean "when in doubt, revoke."

**Non-recursion.** In v0.2, revocations are not themselves subject to
revocation. When the consumer evaluates a `RevocationReceipt` for its own
admissibility, only the base artifact-level checks apply; the consumer does
not search the context for revocations of the revocation.
Revocation-of-revocation semantics are deferred to a later version.

**Deterministic causal parents.** When more than one admissible revocation
binds the same target, the emitted `HandlingReceipt` lists them in
lexicographic order by `artifact_hash` within `causal_parents`, after the
targeted artifact's hash.

## 6. Shared artifact grammar

Every WLP artifact carries:

- `kind` — one of the artifact class names above
- `version` — WLP wire version, e.g., `"0.1"`
- `subject` — a domain-neutral identifier the artifact is about
- `actor` — the party emitting the artifact
- `acted` — for `HandlingReceipt` only: a consumer assertion of whether the
  consumer acted on the parent artifact. `acted` is a consumer assertion in
  the HandlingReceipt, not a conclusion produced by WLP validation. `null`
  on every other artifact class. See [`docs/open-issues.md`](./docs/open-issues.md)
  for the deferred validation/action separation.

…and the following five sections:

### 6.1 `transition` / `claim`

The act or assertion the artifact carries.

- `actor`
- `subject` / `object`
- `operation`
- `target` or state delta, if applicable
- opaque domain `payload` (opaque JSON after canonicalization)

### 6.2 `admissibility`

The conditions under which the artifact has standing to bind.

- `standing` — the actor's claimed standing class
- `scope` — what the artifact covers
- `basis` / `warrant` — the rule cited
- `evidence_refs` — references to supporting evidence
- `policy_refs` — references to the governing policy and version
- `verdict` — for HandlingReceipts, the outer handling verdict (see §7)
- `reason_codes` — open-vocabulary tags explaining the verdict or status

### 6.3 `temporal_envelope`

When the artifact is valid. **This section is mandatory and fail-closed.**

- `issued_at`
- `valid_from`
- `valid_until` — **required**; missing or unparseable ⇒ invalid
- `revalidation_after` (optional)
- `invalidation_conditions` (optional, opaque to WLP)

### 6.4 `custody`

How the artifact is bound to its content and to its lineage.

- `issuer`
- `artifact_hash` — SHA-256 over the RFC 8785 canonical JSON of the artifact
  with the `custody.artifact_hash` and `custody.signature` fields set to `null`
- `signature` — placeholder for v0.1; pluggable later
- `causal_parents` — refs (by `artifact_hash`) to parent artifacts
- `receipt_hash` — optional reference to a publication receipt

### 6.5 `contestability`

How the artifact can be challenged or supplanted.

- `revocation_refs` / `revocation_endpoints`
- `contest_refs` / `contest_endpoints`
- `supersession_refs`
- `degradation_behavior` — what consumers should do under partial loss

## 7. Handling verdicts

The outer handling verdict enum is **closed**. Reason codes are **open**.

Closed enum:

- `accepted`
- `accepted_with_degradation`
- `advisory_only`
- `refused`
- `expired`
- `revoked`
- `contested`
- `unsupported`
- `malformed`

A consumer must select exactly one verdict. Reason codes (strings) may be
added freely and accumulate across the handling chain.

## 8. Fail-closed rules

A WLP validator must refuse or degrade — never silently accept — when:

1. The temporal envelope is missing.
2. `valid_until` is missing or unparseable.
3. The reference time is at or after `valid_until` ⇒ verdict `expired`.
4. Freshness is unknown (no `issued_at` and no `valid_from`) ⇒ no standing.
5. A referenced policy is unsupported by the consumer ⇒ verdict `unsupported`,
   no action taken, no silent downgrade to `accepted`.
6. Scope, evidence, or custody information is lost in handling ⇒ verdict
   `accepted_with_degradation` or `refused`, never `accepted`.
7. An inadmissible `RevocationReceipt` — one that is expired, not-yet-valid,
   policy-less, cites an unsupported policy scheme, or targets an artifact
   other than the one being evaluated — MUST NOT mutate the standing of any
   other artifact. Fail-closed in the revocation direction means *the
   revocation does not bind*, not "when in doubt, revoke."
8. An artifact whose own admissibility check fails returns its own verdict;
   a contemporaneous `RevocationReceipt` does not override that verdict.
   Revocation changes present standing; it does not erase historical
   validity.

## 9. Canonicalization and custody hashes

- Canonical JSON: RFC 8785 (JCS).
- Hash: SHA-256 over canonical JSON bytes.
- Artifact hashes are computed with `custody.artifact_hash` and
  `custody.signature` set to JSON `null` to break the self-reference.
- Hash form on the wire: `"sha256:" + lowercase hex`.

## 10. Transport independence

WLP artifacts are **transport-independent**. WLP makes no assumption about how
an artifact travels — files, queues, HTTP, object storage, signed bundles, and
other substrates are all in scope.

Transport confidentiality and peer authentication are **out of scope for v0.1**,
but any networked WLP deployment must provide them.

Custody and channel security answer different questions and are not
substitutable:

| Channel security (e.g., TLS) answers | WLP custody answers                                   |
| ------------------------------------ | ----------------------------------------------------- |
| Who am I talking to?                 | What artifact is this?                                |
| Is this channel confidential?        | Who issued it?                                        |
| Was the connection tampered with?    | Has the artifact changed?                             |
|                                      | What does it depend on?                               |
|                                      | What happened when it crossed the boundary?          |

The trap to avoid: *"we're using TLS, so the receipt is trustworthy."* TLS
secures the pipe; it does not make the artifact admissible after it leaves the
pipe, gets stored, replayed, forwarded, cached, rendered, or dragged through
integration middleware.

Channel security does not replace artifact custody. Artifact custody does not
replace channel security.

## 11. Test discipline

WLP validators must accept a **deterministic reference time** as input rather
than reading wall-clock `now()`. v0.1 tests pass an explicit reference time;
runtimes are responsible for supplying real time at the boundary.

## 12. v0.1 acceptance

v0.1 is accepted when three fixtures prove the loop:

1. **Expired authorization is refused.** The consumer emits a
   `HandlingReceipt` with verdict `expired`, `acted: false`, and a
   `causal_parents` reference to the expired `AuthorizationReceipt`.
2. **Unsupported policy is refused or degraded.** The consumer emits a
   `HandlingReceipt` with verdict `unsupported`, `acted: false`.
3. **Valid authorization can be handled.** The consumer emits a
   `HandlingReceipt` with verdict `accepted`, `acted: true`, referencing
   the parent `AuthorizationReceipt` by `artifact_hash`.

Anything beyond these three behaviors is out of scope for v0.1.

## 13. v0.2 acceptance

v0.2 widens the consumer to be **graph-aware**: it can evaluate an artifact
in the presence of contextual receipts that mutate its standing. Five
fixture-driven tests prove the forcing case.

The widened API:

```
fn handle(parent: &Artifact, context: &[&Artifact], opts: &HandleOpts) -> Artifact
```

Graph-awareness is wire contract, not opt-in: every consumer must declare a
context (even an empty one).

Required behaviors:

1. **Valid R revokes A.** An admissible `AuthorizationReceipt` A together
   with an admissible `RevocationReceipt` R whose
   `transition.target == parent_hash(A)` yields verdict `revoked`,
   `acted: false`, `causal_parents = [A_hash, R_hash]`.
2. **Future-dated R does not bind.** A R with `valid_from > reference_time`
   leaves A's verdict as `accepted`; R is not recorded in `causal_parents`.
3. **R targeting a different hash does not affect A.** A R with
   `transition.target` set to any hash other than `parent_hash(A)` leaves
   A's verdict as `accepted`.
4. **Policy-less R does not bind.** A R with empty `policy_refs` does not
   mutate A's standing.
5. **Revocation does not launder an already-invalid artifact.** An expired
   `AuthorizationReceipt` together with an admissible `RevocationReceipt`
   targeting it yields verdict `expired` (not `revoked`); only A's hash
   appears in `causal_parents`. Revocation changes present standing; it
   does not erase historical validity.

The v0.1 fixtures continue to pass with the widened signature; existing
consumers pass `&[]` for context.

Anything beyond these five behaviors is out of scope for v0.2. In
particular: no registry, no daemon, no discovery protocol, no global
artifact graph, no key-management expansion, no policy DSL, no transitive
revocation, no "revocation as event stream" shortcut, no CLI surface.
