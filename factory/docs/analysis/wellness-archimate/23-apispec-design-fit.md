# API Specification ⇄ Design Fit Review

Source: `~/Downloads/API Specification.docx` (Naval Arora, Initial Draft, 19 Jun 2026)
Compared against: `19-behaviour-detailed-sequences.md` + `solution-architecture-elk.drawio`

## Scope note
The spec is the **citizen mobile BFF surface** (`/api/mobile/v1`) — it maps to
Sahatna Client → APIM Citizen Gateway → **Gamification Service (BFF)**. It is NOT the
whole platform; admin/partner, B2B, settlement, Malaffi, Event Hub are correctly out of scope.
Judge it as the south-of-the-citizen contract only.

## Well aligned ✓
- Eligibility: `GET /challenges` (eligible+enrolled) + `POST /challenges/eligible` (bulk) ≈ Eligibility Resolver.
- Scoring/Recognition fully surfaced: leaderboard, performance, streak, streak-history, results, period-scores, progress.
- Wallet ledger: balance / history / transaction-details ≈ Wallet–Points Ledger (cumulative, immutable, auditable).
- Marketplace browse + redemption history/details ≈ Marketplace & Voucher stores.
- Conclusion: `GET /challenges/{id}/results` ≈ Phase-5 standings.

## Gaps / misalignments ✗ (ordered by severity)

1. **Redeem saga collapsed to a synchronous call (inv-4/5/8).**
   `POST .../redeem` has an **empty body**, no `Idempotency-Key`, and returns `status:SUCCESS`
   only. Design redeem is a saga: reserve(300s)→inline fraud→partner(10s,3 retries)→confirm/release,
   with `reserved/partner_pending/UNCERTAIN` states and a "try again later" outcome. The contract
   cannot express partner timeout or the uncertain path. Error codes omit fraud-declined and
   reservation-timeout. **→ add async/pending status + polling, idempotency, uncertain handling.**

2. **Idempotency-Key missing.** Drawio (`c126`) and the redeem sequence mandate a client UUIDv4
   Idempotency-Key; Integration-North does an "idempotency relay". Required Headers list only
   Authorization + Content-Type. Every mutating op (enroll, redeem, survey) needs it.

3. **Consent never captured (§2b, §7, inv consent-gate).** Design: enrolment records consent
   "includes NOTIFY consent + channels", propagated to CONS-SVC and checked before any
   notification. `POST .../enroll` has an **empty body** — no consent/channels payload, and
   there are no consent endpoints at all. **→ enroll must carry T&C + notify-consent + channels.**

4. **Wearable telemetry ingestion absent (inv-3 verify-gate, the core Earn loop).** The entire
   earn loop runs on Health Connect SDK telemetry → Wearable Service → Event Hub → Verification.
   The spec's only activity input is `POST /activities/survey`. Telemetry may legitimately flow
   on-device via SDK (not mobile REST), but the contract should state that boundary explicitly,
   else readers assume surveys are the only scoring source.

5. **Withdrawal semantics weaker than design (inv-8).** `POST .../disenroll` says "historical
   scores remain auditable" but the design requires withdrawal to **VOID scoring state +
   streak, irreversible, no credit**. Contract should state the void + irreversibility.

6. **Internal status-enum inconsistency.** `GET /challenges` query enum is ACTIVE/UPCOMING/ENROLLED
   but sample responses use `status:PUBLISHED` and `enrollmentStatus:NOT_STARTED`. Reconcile the
   challenge lifecycle vocabulary (align to design: authored→published→active→concluded→archived).

## Lower-priority observations
- Eligibility `reason` is a flat enum (AGE_RESTRICTION); fine as abstraction, but it hides the
  clinical(Malaffi scoped)/demographic/telemetry segment seam — acceptable for a BFF.
- Challenge detail returns definition + **localized content**, both owned by the Challenge service
  (CMS removed; Sahatna is a thin renderer). The mobile API must therefore honour `Accept-Language`
  (AR/EN) — confirm the contract carries a locale header and per-locale fields.
- Auth says generic "OAuth2/OIDC Bearer"; design citizen path is UAE Pass federation → APIM-minted
  JWT → ID-SVC token exchange. Contract-level wording OK; note the issuer for clarity.

## Bottom line
Satisfies the **read/query** half of the citizen journey strongly. Does **not yet** satisfy the
four hardest design invariants — redeem saga (inv-4/5/8), idempotency, consent gating, and the
verify-gated earn loop. These are correctness/financial/PDPL-load-bearing, so they should be
closed before the contract is treated as complete.
