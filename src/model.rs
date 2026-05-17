//! WLP v0.1 wire model.
//!
//! Every artifact carries the same outer shape: `kind`, `version`, `subject`,
//! `actor`, and five mandatory sections (`transition`, `admissibility`,
//! `temporal_envelope`, `custody`, `contestability`). Optional fields appear
//! on the wire as JSON `null` rather than being omitted — this keeps the
//! canonical form stable across producers and is what makes laundering
//! harder than refusal at the wire layer.
//!
//! See `SPEC.md` §6 for the full grammar.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value;

/// Artifact class. The closed set of WLP v0.1 wire kinds.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Kind {
    ClaimReceipt,
    AuthorizationReceipt,
    HandlingReceipt,
    RevocationReceipt,
    ContestReceipt,
}

/// Closed outer verdict for HandlingReceipts. Reason codes are open.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HandlingVerdict {
    Accepted,
    AcceptedWithDegradation,
    AdvisoryOnly,
    Refused,
    Expired,
    Revoked,
    Contested,
    Unsupported,
    Malformed,
}

/// Reference to a policy that governs an artifact.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyRef {
    pub scheme: String,
    pub id: String,
    pub version: Option<String>,
}

/// The act or assertion the artifact carries.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transition {
    pub actor: String,
    pub subject: String,
    pub object: Option<String>,
    pub operation: String,
    pub target: Option<String>,
    pub payload: Option<Value>,
}

/// Conditions under which the artifact has standing to bind.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Admissibility {
    pub standing: Option<String>,
    pub scope: Option<String>,
    pub basis: Option<String>,
    pub evidence_refs: Vec<String>,
    pub policy_refs: Vec<PolicyRef>,
    /// HandlingReceipts set this. Other artifact classes leave it `None`.
    pub verdict: Option<HandlingVerdict>,
    pub reason_codes: Vec<String>,
}

/// When the artifact is valid. `valid_until` is required; missing or
/// unparseable values fail closed at deserialization.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TemporalEnvelope {
    pub issued_at: DateTime<Utc>,
    pub valid_from: DateTime<Utc>,
    pub valid_until: DateTime<Utc>,
    pub revalidation_after: Option<DateTime<Utc>>,
    pub invalidation_conditions: Option<Value>,
}

/// How the artifact is bound to its content and lineage.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Custody {
    pub issuer: String,
    /// `sha256:<hex>` over the RFC 8785 canonical JSON of the artifact with
    /// `custody.artifact_hash` and `custody.signature` nulled. `None` on the
    /// wire means "issuer did not stamp"; consumers may recompute.
    pub artifact_hash: Option<String>,
    /// Pluggable in a later version; `None` for v0.1.
    pub signature: Option<String>,
    pub causal_parents: Vec<String>,
    pub receipt_hash: Option<String>,
}

/// How the artifact can be challenged or supplanted.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Contestability {
    pub revocation_refs: Vec<String>,
    pub revocation_endpoints: Vec<String>,
    pub contest_refs: Vec<String>,
    pub contest_endpoints: Vec<String>,
    pub supersession_refs: Vec<String>,
    pub degradation_behavior: Option<String>,
}

/// A complete WLP artifact.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Artifact {
    pub kind: Kind,
    pub version: String,
    pub subject: String,
    pub actor: String,
    pub transition: Option<Transition>,
    pub admissibility: Admissibility,
    pub temporal_envelope: TemporalEnvelope,
    pub custody: Custody,
    pub contestability: Contestability,
    /// HandlingReceipts state whether the consumer acted. `None` for other
    /// artifact classes.
    pub acted: Option<bool>,
}
