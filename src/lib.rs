//! # WLP — Wire protocol for preserving admissibility across system boundaries.
//!
//! WLP is domain-semantically neutral and admissibility-semantically opinionated.
//!
//! WLP validates artifacts. It does **not** decide whether the world should
//! have produced them.
//!
//! See `README.md` and `SPEC.md` at the repo root for the v0.1 constitution
//! and acceptance criteria. v0.1 artifact classes:
//!
//! - `ClaimReceipt`
//! - `AuthorizationReceipt`
//! - `HandlingReceipt`
//! - `RevocationReceipt`
//! - `ContestReceipt`
//!
//! Constitution: every WLP artifact must carry the terms under which it
//! stops binding. Missing or unparseable expiry fails closed.
