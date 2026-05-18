//! Canonicalization equivalence (custody plumbing).
//!
//! Same artifact, different JSON key order/whitespace ⇒ same custody hash.
//! RFC 8785 canonicalization erases formatting differences before sha256 is
//! taken. This test pins that property at the wire layer so a future change
//! to the hashing pipeline cannot silently break custody agreement between
//! producers that format JSON differently.

use wlp::{artifact_hash, Artifact};

fn load(name: &str) -> Artifact {
    let path = format!("tests/fixtures/{name}");
    let body =
        std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("read fixture {path}: {e}"));
    serde_json::from_str(&body).unwrap_or_else(|e| panic!("parse fixture {path}: {e}"))
}

#[test]
fn canonical_hash_is_independent_of_json_formatting() {
    let a = load("canonical_equivalence_a.json");
    let b = load("canonical_equivalence_b.json");

    let hash_a = artifact_hash(&a);
    let hash_b = artifact_hash(&b);

    assert!(
        hash_a.starts_with("sha256:"),
        "hash must use the sha256: wire form (SPEC §9): {hash_a}",
    );
    assert_eq!(
        hash_a, hash_b,
        "the same logical artifact must hash identically regardless of \
         JSON key order or whitespace — RFC 8785 canonicalization is the \
         contract that keeps custody agreement honest across producers",
    );
}
