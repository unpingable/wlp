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

use crate::model::Artifact;
use chrono::{DateTime, Utc};

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
    let _ = (parent, opts);
    unimplemented!("handle() lands in commit 3")
}
