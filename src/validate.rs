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

/// Inspect `parent` and emit a HandlingReceipt that records what happened.
pub fn handle(parent: &Artifact, opts: &HandleOpts) -> Artifact {
    let parent_hash = artifact_hash(parent);
    let (verdict, reason_codes, acted) = decide(parent, opts);

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
            evidence_refs: vec![parent_hash.clone()],
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
            causal_parents: vec![parent_hash],
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
    // §8.3 — expiry check first. An expired authorization gets no further
    // consideration; we do not look at its policy.
    if opts.reference_time >= parent.temporal_envelope.valid_until {
        return (
            HandlingVerdict::Expired,
            vec!["envelope_expired".to_string()],
            false,
        );
    }

    // §8.5 — unsupported policy scheme must not silently downgrade to accept.
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
