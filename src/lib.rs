//! # WLP — Wire protocol for preserving admissibility across system boundaries.
//!
//! WLP is domain-semantically neutral and admissibility-semantically opinionated.
//!
//! WLP validates artifacts. It does **not** decide whether the world should
//! have produced them.
//!
//! See `README.md` and `SPEC.md` at the repo root for the v0.1 constitution
//! and acceptance criteria.

pub mod canonical;
pub mod model;
pub mod validate;

pub use canonical::artifact_hash;
pub use model::{
    Admissibility, Artifact, Contestability, Custody, HandlingVerdict, Kind, PolicyRef,
    TemporalEnvelope, Transition,
};
pub use validate::{handle, HandleOpts};
