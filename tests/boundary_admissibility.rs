//! v0.1 acceptance — the three required behaviors (SPEC §12).
//!
//! Each test exercises the clean v0.1 loop:
//!
//!     producer  emits AuthorizationReceipt  (loaded from fixture JSON)
//!     consumer  validates envelope/custody/standing  (handle())
//!     consumer  emits HandlingReceipt        (return value)
//!
//! Tests pass a deterministic `reference_time`; no wall-clock reads.

use chrono::{DateTime, Utc};
use wlp::{artifact_hash, handle, Artifact, HandleOpts, HandlingVerdict, Kind};

const REF_TIME: &str = "2026-05-17T12:00:00Z";

fn ref_time() -> DateTime<Utc> {
    REF_TIME.parse().expect("REF_TIME is RFC 3339")
}

fn load(name: &str) -> Artifact {
    let path = format!("tests/fixtures/{name}");
    let body =
        std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read fixture {path}: {e}"));
    serde_json::from_str(&body).unwrap_or_else(|e| panic!("parse fixture {path}: {e}"))
}

fn opts_supporting_change_policy() -> HandleOpts {
    HandleOpts {
        consumer: "system-b".to_string(),
        reference_time: ref_time(),
        supported_policy_schemes: vec!["change-policy".to_string()],
    }
}

#[test]
fn expired_authorization_is_refused_with_handling_receipt() {
    let parent = load("expired_authorization.json");
    let receipt = handle(&parent, &opts_supporting_change_policy());

    assert_eq!(receipt.kind, Kind::HandlingReceipt);
    assert_eq!(
        receipt.admissibility.verdict,
        Some(HandlingVerdict::Expired),
        "expired authorization must yield verdict `expired`, not silent accept",
    );
    assert_eq!(receipt.acted, Some(false), "expired ⇒ acted: false");

    assert_eq!(
        receipt.custody.causal_parents.len(),
        1,
        "HandlingReceipt must reference its parent by content hash",
    );
    let parent_hash = artifact_hash(&parent);
    assert_eq!(
        receipt.custody.causal_parents[0], parent_hash,
        "child causal_parent[0] must equal the parent's artifact_hash",
    );

    assert!(
        receipt
            .admissibility
            .reason_codes
            .iter()
            .any(|c| c.contains("expired") || c.contains("envelope")),
        "reason_codes should surface the expiry: {:?}",
        receipt.admissibility.reason_codes,
    );
}

#[test]
fn unsupported_policy_is_refused_not_silently_accepted() {
    let parent = load("unsupported_policy.json");
    let receipt = handle(&parent, &opts_supporting_change_policy());

    assert_eq!(receipt.kind, Kind::HandlingReceipt);
    assert_eq!(
        receipt.admissibility.verdict,
        Some(HandlingVerdict::Unsupported),
        "unknown policy scheme must yield `unsupported`, never silent accept",
    );
    assert_eq!(receipt.acted, Some(false), "unsupported ⇒ acted: false");

    let parent_hash = artifact_hash(&parent);
    assert_eq!(receipt.custody.causal_parents, vec![parent_hash]);

    assert!(
        receipt
            .admissibility
            .reason_codes
            .iter()
            .any(|c| c.contains("policy")),
        "reason_codes should name the policy gap: {:?}",
        receipt.admissibility.reason_codes,
    );
}

#[test]
fn valid_authorization_handled_with_child_receipt_referencing_parent() {
    let parent = load("valid_authorization.json");
    let receipt = handle(&parent, &opts_supporting_change_policy());

    assert_eq!(receipt.kind, Kind::HandlingReceipt);
    assert_eq!(
        receipt.admissibility.verdict,
        Some(HandlingVerdict::Accepted),
        "valid envelope + supported policy ⇒ accepted",
    );
    assert_eq!(receipt.acted, Some(true), "accepted ⇒ acted: true");

    let parent_hash = artifact_hash(&parent);
    assert_eq!(
        receipt.custody.causal_parents,
        vec![parent_hash],
        "child must reference the parent's content hash",
    );

    assert!(
        receipt.custody.causal_parents[0].starts_with("sha256:"),
        "parent ref must use the sha256: hash form (SPEC §9)",
    );

    assert_eq!(
        receipt.actor, "system-b",
        "HandlingReceipt is emitted by the consumer",
    );
    assert_eq!(receipt.custody.issuer, "system-b");

    // Receipt has its own well-formed envelope (constitution: every artifact
    // carries the terms under which it stops binding).
    let env = &receipt.temporal_envelope;
    assert_eq!(env.issued_at, ref_time());
    assert!(
        env.valid_until > env.issued_at,
        "receipt must expire later than it was issued"
    );
}
