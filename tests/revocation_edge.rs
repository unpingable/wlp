//! v0.2 acceptance — graph-aware evaluation in the presence of RevocationReceipts.
//!
//! Each test exercises whether a consumer correctly distinguishes admissible
//! revocations (which mutate present standing) from inadmissible ones (which
//! must not bind). Fixture R artifacts use a placeholder
//! `transition.target` of `sha256:000...0`; tests that should target A patch
//! the field at runtime via `target_a()`. The "targets-other" test uses a
//! distinct fixture with a literal non-matching hash and does not patch.
//!
//! SPEC §13. Tests pass a deterministic reference time.

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

fn opts() -> HandleOpts {
    HandleOpts {
        consumer: "system-b".to_string(),
        reference_time: ref_time(),
        supported_policy_schemes: vec!["change-policy".to_string()],
    }
}

/// Patch R's `transition.target` so it targets `parent_hash(a)`.
fn target_a(mut r: Artifact, a: &Artifact) -> Artifact {
    let h = artifact_hash(a);
    r.transition
        .as_mut()
        .expect("R fixture must carry a transition section")
        .target = Some(h);
    r
}

#[test]
fn valid_revocation_revokes_admissible_authorization() {
    let a = load("valid_authorization.json");
    let r = target_a(load("valid_revocation.json"), &a);
    let receipt = handle(&a, &[&r], &opts());

    assert_eq!(receipt.kind, Kind::HandlingReceipt);
    assert_eq!(
        receipt.admissibility.verdict,
        Some(HandlingVerdict::Revoked),
        "admissible R targeting A must yield verdict=revoked",
    );
    assert_eq!(receipt.acted, Some(false));

    let a_hash = artifact_hash(&a);
    let r_hash = artifact_hash(&r);
    assert_eq!(
        receipt.custody.causal_parents,
        vec![a_hash, r_hash],
        "causal_parents must list [A_hash, R_hash] in that order",
    );

    assert!(
        receipt
            .admissibility
            .reason_codes
            .iter()
            .any(|c| c == "authorization_revoked"),
        "reason_codes must include 'authorization_revoked': {:?}",
        receipt.admissibility.reason_codes,
    );
}

#[test]
fn future_dated_revocation_does_not_bind() {
    let a = load("valid_authorization.json");
    let r = target_a(load("future_dated_revocation.json"), &a);
    let receipt = handle(&a, &[&r], &opts());

    assert_eq!(
        receipt.admissibility.verdict,
        Some(HandlingVerdict::Accepted),
        "future-dated R is itself inadmissible and must not bind A",
    );
    assert_eq!(receipt.acted, Some(true));

    let a_hash = artifact_hash(&a);
    assert_eq!(
        receipt.custody.causal_parents,
        vec![a_hash],
        "non-binding R must not appear in causal_parents",
    );
}

#[test]
fn revocation_targeting_other_artifact_does_not_affect_subject() {
    let a = load("valid_authorization.json");
    // Fixture's transition.target is left as a literal non-A hash (no patching).
    let r = load("revocation_targeting_other.json");
    let receipt = handle(&a, &[&r], &opts());

    assert_eq!(
        receipt.admissibility.verdict,
        Some(HandlingVerdict::Accepted),
        "R whose transition.target ≠ parent_hash(A) must not affect A's standing",
    );
    assert_eq!(receipt.acted, Some(true));

    let a_hash = artifact_hash(&a);
    assert_eq!(receipt.custody.causal_parents, vec![a_hash]);
}

#[test]
fn policy_less_revocation_does_not_bind() {
    let a = load("valid_authorization.json");
    let r = target_a(load("policy_less_revocation.json"), &a);
    let receipt = handle(&a, &[&r], &opts());

    assert_eq!(
        receipt.admissibility.verdict,
        Some(HandlingVerdict::Accepted),
        "R that fails its own admissibility (no policy_refs) must not bind A — \
         fail-closed for revocation means R does not bind, not 'when in doubt, revoke'",
    );
    assert_eq!(receipt.acted, Some(true));

    let a_hash = artifact_hash(&a);
    assert_eq!(receipt.custody.causal_parents, vec![a_hash]);
}

#[test]
fn revocation_does_not_launder_an_already_invalid_artifact() {
    let a = load("expired_authorization.json");
    let r = target_a(load("valid_revocation.json"), &a);
    let receipt = handle(&a, &[&r], &opts());

    assert_eq!(
        receipt.admissibility.verdict,
        Some(HandlingVerdict::Expired),
        "expired A returns its own verdict; revocation does not erase history",
    );
    assert_eq!(receipt.acted, Some(false));

    let a_hash = artifact_hash(&a);
    assert_eq!(
        receipt.custody.causal_parents,
        vec![a_hash],
        "when A fails its own check, R never binds and is not in causal_parents",
    );
}
