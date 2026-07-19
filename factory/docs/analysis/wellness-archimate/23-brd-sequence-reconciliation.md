# BRD ↔ Behaviour-Sequence Reconciliation (`19-behaviour-detailed-sequences.md`)

Source of truth: **`Wellnes-Gamefication-BRD.docx`** (extracted → `wellness-brd-extracted.md`, ~30k words,
6 H1 / 21 H2 / 65 H3). Grounding = literal term counts in the BRD body.

## Headline — the two documents model different spines
- **Sequences** (`19-…`) are built on a **clinical-eligibility + partner-settlement** spine (Malaffi scoped
  membership, Reward-Provider redemption, DoH settlement/holdback).
- **BRD** is a **gamification-competition** spine: Goals, **Streaks (27)**, **Teams (90)**, **Districts (74)**,
  **Leaderboards (37)**, **Badges (27)**, Titles/Levels (Perfect Week ×9), **Quests/Events/Screenings**
  (Citymoov 8 · IFHAS 6 · screening 10), Marketplace (inventory/expiry/QR).
- **`clinical` = 0**, **`Malaffi` = 2**, **`settlement`/`holdback` = 0** in the BRD → the sequences' central
  clinical and settlement flows are **architecture assumptions (from `18-eligibility-…`), not BRD requirements.**
- **Phase 1 = "individual-based challenges only"** (per Phase-1 Scope). Team/District is Phase 2/3 — so those
  gaps are real but **not Phase-1-blocking**.

## Coverage matrix (BRD area → sequence)
| BRD area | Status | Where / gap |
|---|---|---|
| Challenge **Structure & Lifecycle** (author→publish→conclude) | ✅ Covered | §1 + master Phase 1/5 |
| **Eligibility & Audience Targeting** (segment age/gender/conditions, whitelist, accessibility) | ⚠ Divergent | §2 models Malaffi **clinical** membership; BRD = segment **attributes** (no Malaffi) |
| **Enrollment** discovery + general opt-in flow | ✅ Covered | §2 / §2b |
| **Disenrollment / Withdrawal** | ✅ Covered | §2b Withdrawal opt (voids score) |
| **Reward Points** earn/wallet/redeem (append-only, idempotent) | ✅ Covered | §3 credit + §4 redeem |
| **Communication Enablement / Nudges** (consent-gated) | ✅ Covered | §7 Notification |
| **Goals**: assignment models (**segment-fixed + baseline-personalized**), locking, visibility | ⚠ Partial | §1 freezes one ScoringPlan; per-user baseline goal **computation at enrol** + goal-locking not modelled |
| **Scoring**: individual weekly + finalization, **week closure**, **tie-breaking** | ⚠ Partial | §3 individual; no finalize/tie-break sequence |
| **Streaks**: daily→weekly counter→end-of-week→edge cases | ⚠ Partial | §3 name-drops "streak"; no streak-eval sequence |
| **Marketplace** ops: **inventory**, **QR reward**, **expiry**, post-redemption | ⚠ Partial | §4 issues a voucher only; inventory/QR/expiry absent |
| **Challenge Request → Review → Approval → Configuration** (program team + ADHDS) | ❌ Missing | §1 starts at Admin authoring — skips request/review/approve/go-live |
| **Additional Goal Types**: Quest (Citymoov) · Event (Sahatna) · Screening (IFHAS) | ❌ Missing | Earn loop ingests only wearable + Sahatna telemetry |
| **Leaderboard**: Individual/Team/Hybrid/District, ranking, tie-break | ❌ Missing | no leaderboard read/compute/display sequence |
| **Badges** (award + screen + moment-of-achievement) | ❌ Missing | — |
| **Titles / Levels** (level structure, progression, advancement thresholds, **Perfect Week**) | ❌ Missing | "Scoring Recognition" name-drops titles/badges; no progression flow |
| **Team Score** + **Team Enrollment** (create/join/individual, constraints) | ❌ Missing (Phase 2) | — |
| **District Score** + **District Enrollment** (derive/select, constraints) | ❌ Missing (Phase 2/3) | — |
| **Winning Criteria → Reward Mapping** + **Winner Allocation** + winner-list **review/approval** | ❌ Missing | conclusion is a one-line hand-off; no winner-list approval loop |
| **Governance & Operational Controls**, **Score Validation/Audit** | ⚠ Partial | FRAUD-SVC async only |

## Gaps → new sequences to add (Phase-1 first)
1. **Challenge Request & Approval** — requester → program-team review → approve → ADHDS configure → go-live. *(governance, missing entirely)*
2. **Goal Assignment & Locking** — at enrol: resolve segment-fixed vs **baseline-personalized** goal, lock for challenge duration.
3. **Streak Evaluation** — daily success → weekly counter → end-of-week → edge cases (gap day, partial week).
4. **Score Finalization & Week Closure** — real-time update → week close → finalize → **tie-break** → standings.
5. **Leaderboard (Individual)** — read finalized scores → rank → tie-break → display (Team/Hybrid/District = Phase 2/3 variants).
6. **Badges & Titles/Levels** — award on Perfect Week / advancement thresholds → badge screen.
7. **Alternate activity sources** — Quest (Citymoov), Event (Sahatna), Screening (IFHAS) → verified-activity ingest into the Earn loop.
8. **Marketplace ops** — inventory reserve/decrement, **QR** reward, expiry handling, post-redemption.
*(Phase 2/3): Team create/join + team scoring + team leaderboard; District derive/select + district scoring + district leaderboard.)*

## Divergences to confirm (sequence content NOT in this BRD)
- **Clinical / Malaffi eligibility** (§2 alt-branch) — confirm whether the BRD's "conditions" segment is the
  Malaffi hook, or drop the clinical branch as out-of-scope for this BRD.
- **Settlement / holdback / VAT / DoH ESB** (§5) — absent from the BRD (0 hits); confirm it's partner-track / Phase 4.
- **UAE Pass / Entra identity federation** — platform-architecture detail, BRD-silent (acceptable).

## Note
Sequences' Part-B two-way audit holds *against the C4 model*, not the BRD. This reconciliation adds the
**third leg** (BRD ↔ sequences). Open Questions / Non-functional / Performance-Metrics BRD sections are
requirement-level, not runtime sequences (no flow expected).
