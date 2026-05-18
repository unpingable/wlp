//! Admissibility check + HandlingReceipt emission.
//!
//! v0.1: `handle()` is the v0.1 loop's consumer side. Given a parent artifact
//! (typically an `AuthorizationReceipt`), the consumer's identity, a
//! deterministic reference time, and the policy schemes the consumer supports,
//! it returns a `HandlingReceipt` recording what happened.
//!
//! This module makes no decision about whether the world should have produced
//! the parent. It only inspects whether the parent's admissibility surface
//! survived the boundary.

use crate::canonical::artifact_hash;
use crate::model::{
    Admissibility, Artifact, Contestability, Custody, HandlingVerdict, Kind, TemporalEnvelope,
    Transition,
};
use chrono::{DateTime, Duration, Utc};

/// HandlingReceipts are emitted with a 24h validity window. Long-term
/// preservation is the job of a downstream durable layer (out of scope for
/// WLP, per SPEC §1 — WLP does not decide what must enter a ledger).
const RECEIPT_VALIDITY_HOURS: i64 = 24;

/// Inputs to the consumer-side handling loop.
pub struct HandleOpts {
    /// The identity of the consumer emitting the HandlingReceipt.
    pub consumer: String,
    /// Deterministic reference time. Validators must not read wall-clock now.
    pub reference_time: DateTime<Utc>,
    /// Policy schemes (e.g., `"change-policy"`) this consumer understands.
    pub supported_policy_schemes: Vec<String>,
}

/// Inspect `parent` in the presence of `context` and emit a HandlingReceipt
/// that records what happened.
///
/// `context` is the set of other WLP artifacts the consumer has admitted into
/// scope. v0.2 considers `RevocationReceipt` entries whose `transition.target`
/// equals `parent`'s `artifact_hash`; if the revocation is itself admissible
/// (envelope valid, policy_refs non-empty, schemes supported), it mutates the
/// parent's present standing to `revoked`.
///
/// A revocation does not erase historical validity (SPEC §8.8). If `parent`
/// fails its own admissibility check, the receipt returns parent's own verdict;
/// contextual revocations do not override it.
pub fn handle(parent: &Artifact, context: &[&Artifact], opts: &HandleOpts) -> Artifact {
    let parent_hash = artifact_hash(parent);
    let (mut verdict, mut reason_codes, mut acted) = decide(parent, opts);
    let mut causal_parents = vec![parent_hash.clone()];

    // §8.8: A's own failure is preserved; revocation never erases history.
    // Only walk context when parent is otherwise accepted.
    if matches!(verdict, HandlingVerdict::Accepted) {
        let mut binding_revocations: Vec<String> = Vec::new();
        for r in context {
            if r.kind != Kind::RevocationReceipt {
                continue;
            }
            let targets_parent = r
                .transition
                .as_ref()
                .and_then(|t| t.target.as_deref())
                .map(|t| t == parent_hash)
                .unwrap_or(false);
            if !targets_parent {
                continue;
            }
            // §5.1 non-recursion: R's admissibility uses base artifact-level
            // checks only. We do not search context for revocations of R.
            let (r_verdict, _, _) = decide(r, opts);
            if matches!(r_verdict, HandlingVerdict::Accepted) {
                binding_revocations.push(artifact_hash(r));
            }
        }
        if !binding_revocations.is_empty() {
            // §5.1 deterministic causal_parents: lexicographic by hash.
            binding_revocations.sort();
            verdict = HandlingVerdict::Revoked;
            reason_codes = vec!["authorization_revoked".to_string()];
            acted = false;
            causal_parents.extend(binding_revocations);
        }
    }

    let now = opts.reference_time;
    let mut receipt = Artifact {
        kind: Kind::HandlingReceipt,
        version: "0.1".to_string(),
        subject: parent.subject.clone(),
        actor: opts.consumer.clone(),
        transition: Some(Transition {
            actor: opts.consumer.clone(),
            subject: parent.subject.clone(),
            object: None,
            operation: "handle".to_string(),
            target: None,
            payload: None,
        }),
        admissibility: Admissibility {
            standing: None,
            scope: Some(parent.subject.clone()),
            basis: None,
            evidence_refs: vec![parent_hash],
            policy_refs: vec![],
            verdict: Some(verdict),
            reason_codes,
        },
        temporal_envelope: TemporalEnvelope {
            issued_at: now,
            valid_from: now,
            valid_until: now + Duration::hours(RECEIPT_VALIDITY_HOURS),
            revalidation_after: None,
            invalidation_conditions: None,
        },
        custody: Custody {
            issuer: opts.consumer.clone(),
            artifact_hash: None,
            signature: None,
            causal_parents,
            receipt_hash: None,
        },
        contestability: Contestability {
            revocation_refs: vec![],
            revocation_endpoints: vec![],
            contest_refs: vec![],
            contest_endpoints: vec![],
            supersession_refs: vec![],
            degradation_behavior: None,
        },
        acted: Some(acted),
    };

    // Self-stamp: compute and fill the receipt's own artifact hash. The
    // hash is computed with custody.artifact_hash null, so consumers can
    // recompute and verify.
    receipt.custody.artifact_hash = Some(artifact_hash(&receipt));
    receipt
}

/// Decide the handling verdict in fail-closed priority order (SPEC §8).
fn decide(parent: &Artifact, opts: &HandleOpts) -> (HandlingVerdict, Vec<String>, bool) {
    let env = &parent.temporal_envelope;

    // Expired wins first: a stale envelope gets no further consideration.
    if opts.reference_time >= env.valid_until {
        return (
            HandlingVerdict::Expired,
            vec!["envelope_expired".to_string()],
            false,
        );
    }

    // Not-yet-valid: an artifact whose validity window is still in the future
    // has no current standing. Use Refused (Expired is wrong-direction);
    // explicit reason code carries the temporal semantics.
    if opts.reference_time < env.valid_from {
        return (
            HandlingVerdict::Refused,
            vec!["artifact_not_yet_valid".to_string()],
            false,
        );
    }

    // Missing policy basis: a consumer cannot claim to understand a policy
    // scheme that was never named. Operationally unsupported, not malformed
    // (the wire shape is fine; what's missing is the policy citation).
    if parent.admissibility.policy_refs.is_empty() {
        return (
            HandlingVerdict::Unsupported,
            vec!["policy_refs_missing".to_string()],
            false,
        );
    }

    // Unknown policy scheme must not silently downgrade to accept.
    let unsupported: Vec<String> = parent
        .admissibility
        .policy_refs
        .iter()
        .filter(|p| !opts.supported_policy_schemes.contains(&p.scheme))
        .map(|p| format!("policy_scheme_unsupported:{}", p.scheme))
        .collect();
    if !unsupported.is_empty() {
        return (HandlingVerdict::Unsupported, unsupported, false);
    }

    (
        HandlingVerdict::Accepted,
        vec!["envelope_valid".to_string(), "policy_supported".to_string()],
        true,
    )
}
