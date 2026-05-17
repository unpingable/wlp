//! Canonical JSON and content-addressed custody hashes (SPEC §9).
//!
//! Hash form on the wire: `sha256:` followed by lowercase hex. The hash is
//! computed over the RFC 8785 canonical JSON of the artifact with
//! `custody.artifact_hash` and `custody.signature` set to JSON null to break
//! the self-reference.

use crate::model::Artifact;
use serde_json::Value;
use sha2::{Digest, Sha256};

/// Compute the canonical artifact hash for `artifact`.
pub fn artifact_hash(artifact: &Artifact) -> String {
    let mut v: Value = serde_json::to_value(artifact).expect("Artifact serializes to JSON");
    if let Some(custody) = v.get_mut("custody").and_then(|c| c.as_object_mut()) {
        custody.insert("artifact_hash".into(), Value::Null);
        custody.insert("signature".into(), Value::Null);
    }
    let canonical = serde_jcs::to_string(&v).expect("Value serializes as canonical JSON");
    let mut h = Sha256::new();
    h.update(canonical.as_bytes());
    let digest = h.finalize();
    let hex: String = digest.iter().map(|b| format!("{:02x}", b)).collect();
    format!("sha256:{hex}")
}
