# Functional Gap Analysis — Sahatna Points Wellness Platform

> Scope: FUNCTIONAL / business-logic gaps only. Reviewed against `00-business-requirements-and-rules.md` (8 load-bearing invariants) and `partials/part-1..4.md` (full BR-*/RULE-* catalogue). A "gap" here is a capability or rule a UAE public-health reward platform of this kind clearly needs, that is MISSING or UNDER-SPECIFIED. Items already covered (Wallet ledger, two-phase redemption reservation, partner KYB, settlement holdback, consent-gated nudges, scoring kernel, withdrawal-voids-rewards) are deliberately NOT listed.

## Executive Summary — Most Material Gaps

- **Member identity proofing is effectively absent while partner KYB is rigorous.** Eligibility is purely cohort/segment-based (BR-004/005). There is no age minimum, no minors/guardian-consent rule, and no residency/eligibility proofing for the natural person — a serious omission for a Department of Health platform that grants redeemable monetary value and, in UAE, has a legal age-of-majority and minor-data-consent dimension (PDPL).
- **There is no member-facing dispute or appeal path.** Members can *see* a score breakdown (BR-319) but cannot contest a score, a denied goal, or a failed redemption. Partners get a 30-day settlement dispute window (RULE-215); members get nothing. For a government wellness scheme this is both a fairness and a regulatory-grievance gap.
- **"Points never expire/reset" (RULE-321) is stated as an invariant but never reasoned about as a liability.** No dormancy, breakage, escheatment, or tax/zakat-treatment rule exists. Cumulative non-expiring points of monetary value are an unbounded and unaudited financial liability on the DoH balance sheet.
- **Clawback / fraud-reversal of already-credited (and possibly already-spent) points is undefined.** RULE-219 forbids negative balances, but no rule says what happens when a fraud reversal *would* drive a balance negative — leaving the most important fraud-remediation action unspecified despite a whole FRAUD-SVC (BR-121).
- **Activity anti-cheat and wearable equity are named but not defined.** ACTV-SVC is "the trust gate" and FRAUD-SVC must stop "false activity claims" (BR-121), yet there are zero concrete rules for step-gaming, manual-entry abuse, multi-device double-counting, or a non-wearable earning path — making Steps/Sleep goals (RULE-316) inaccessible and inequitable for members without a wearable.
- **Week-close boundary semantics are under-specified.** Monday reset and credit-at-week-close exist (RULE-317/319) but the controlling timezone (GST vs UTC), a grace window, and how a late-verified activity is attributed to an already-closed week are undefined — directly affecting points correctness near boundaries.

---

## A. Member Identity, Eligibility & Minors

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F01** | No **age minimum** for member participation. Eligibility is segment-membership only (BR-005). | Granting redeemable monetary value to a minor without controls breaches UAE age-of-majority norms and PDPL minor-data provisions; reputational risk for a DoH scheme. | Add **RULE: minimum participation age = 18** (or, if minors are in-scope, a guardian-consent path). Enforce at enrolment alongside the segment-eligibility check (BR-005). | High |
| **GAP-F02** | No **guardian/parental consent** flow for any minor cohort. | If minors are ever segmented in, there is no lawful basis to process their data or issue vouchers. | Add **BR: Minor enrolment requires verified guardian identity + recorded guardian consent_set**, versioned like RULE-011; block redemption for minor wallets without it. | High |
| **GAP-F03** | No **residency / natural-person eligibility verification** (Emirates ID, residency status). ID-SVC exists (BR-119/120) but only links/unlinks an identity; it asserts no proofing strength. | DoH reward eligibility is typically residency-bound; unverified members enable duplicate-identity farming and out-of-scope claimants. | Add **RULE: member identity must be proofed to [Emirates-ID / UAE PASS] assurance level before first credit**, mirroring the rigour KYB applies to partners (RULE-207/208). | High |
| **GAP-F04** | No **duplicate-identity / one-person-one-account** rule. | Multi-account farming directly inflates the points liability and corrupts leaderboards. | Add **RULE: one active member wallet per proofed natural identity**; FRAUD-SVC flags identity collisions before value transfer (extends BR-122). | Med |

## B. Member Dispute, Appeal & Grievance

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F05** | No **member-facing dispute/appeal** for a contested score, a denied/incomplete goal, or a denied enrolment. Only a *view* exists (BR-319). | Government schemes must offer a grievance route; silent denials erode trust and invite escalation to the regulator. | Add **BR: member may raise a scored-period dispute within N days of week-close; dispute freezes affected ledger entries pending adjudication; resolution emits `score.dispute.resolved`**. | High |
| **GAP-F06** | No **member appeal for a failed/uncertain redemption.** BR-221 only "notifies and logs to FRAUD-SVC"; RULE-222 resolves "uncertain" by *admin*, not by member request. | Member whose points were reserved/lost on a failed voucher has no self-service recourse; manual-only resolution does not scale. | Add **BR: member-initiated redemption-inquiry that triggers PartnerAdapter.inquire() (BR-310) and surfaces a status + auto-release/refund decision** within an SLA. | Med |
| **GAP-F07** | No **defined adjudication process / SLA / authority** behind any dispute (member or the partner 30-day window in RULE-215). | A dispute *window* without a *process* is unenforceable and audit-weak. | Add **RULE: dispute adjudication owner, evidence set, decision SLA, and appeal-to-DoH escalation** for both member and partner disputes. | Med |

## C. Points Lifecycle & Financial Liability

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F08** | "Points cumulative, never reset" (RULE-321) has **no expiry / dormancy / breakage policy** and no stated rationale for being permanent. | Non-expiring monetary-value points are an unbounded, ever-growing liability with no breakage relief — a balance-sheet and audit problem for DoH. | Add an explicit **decision RULE**: either (a) confirm "no expiry" as a deliberate policy *with* a liability-accrual + periodic-true-up rule, or (b) introduce dormancy/expiry (e.g. expire after X months of inactivity, emitting `points.expired`). | High |
| **GAP-F09** | No **tax / zakat / reportable-benefit treatment** of earned points or redeemed vouchers. | Vouchers of AED value may be a reportable benefit; absence of a position creates compliance exposure and partner-invoice (VAT, BR-223) inconsistency. | Add **RULE: tax/zakat classification of redemptions and the reporting obligation**, aligned with the VAT-compliant invoicing already in BR-223. | Med |
| **GAP-F10** | No **clawback / negative-balance-on-fraud-reversal** rule. RULE-219 forbids negative balances but is silent on reversals that would breach it. | Without clawback semantics, fraudulently earned points that were already spent cannot be recovered — defeating the purpose of FRAUD-SVC (BR-121). | Add **RULE: fraud reversal creates a compensating double-entry that may drive a `negative recoverable balance` (distinct from spendable balance), blocking future credits until cleared; emits `wallet.clawback.opened`**. | High |
| **GAP-F11** | No **escheatment / scheme-wind-down** handling for outstanding member balances. | If the DoH scheme ends, the disposition of accrued non-expiring points is undefined. | Add **RULE: on scheme termination, outstanding-balance disposition (grace redemption window then forfeiture, mirroring partner offboarding RULE-218)**. | Low |

## D. Week-Close & Scoring Boundary

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F12** | The **controlling timezone** for "week", "Monday reset" and "week close" (RULE-317/319/324) is undefined (GST? UTC?). | Boundary ambiguity changes which day/week an activity scores into, causing reproducibility and dispute risk. | Add **RULE: all week/day boundaries computed in Asia/Dubai (GST, UTC+4); week-close instant = Monday 00:00 GST**. | High |
| **GAP-F13** | No **grace window / late-arrival attribution** for verified activities arriving after week-close. A "Late-Sync Reconciler" is *named* (RULE-203) but its policy is undefined. | A wearable that syncs late could be silently dropped or wrongly credited to the new week, under- or over-counting score. | Add **RULE: verified activity with an effective timestamp inside a closed week is attributed to that week if received within a defined grace window (e.g. 48h); beyond grace it is discarded with `activity.late.discarded`**. | High |
| **GAP-F14** | No rule for **recompute / re-credit** when a late activity changes an already-credited WeeklyScore. | Credits are idempotent (RULE-027) but there is no idempotent *correction* path. | Add **RULE: in-grace late activity triggers an idempotent score-delta credit keyed to the original week-close event; no double credit**. | Med |

## E. Activity Anti-Cheat & Equity

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F15** | No concrete **step-count gaming** controls (vehicle motion, device shaking, implausible rates). Only generic per-day caps (RULE-316) and an undefined "trust gate". | Step inflation is the single most common wellness-app fraud; caps blunt value but do not detect cheating. | Add **RULE: ACTV-SVC validates step plausibility (max steps/min, motion-context, source-attestation) before `activity.verified`; failures emit `activity.rejected{reason}`**. | High |
| **GAP-F16** | No **manual-entry abuse** rule. BR-113 accepts wearable/survey/check-in submissions with no integrity differentiation. | Self-entered metrics are trivially gamed if scored equally to device-attested ones. | Add **RULE: manually entered activity is either non-scoring or capped/flagged; device-attested signals required for value-bearing goals**. | High |
| **GAP-F17** | No **multi-device / double-counting dedup** rule. | A member pairing two wearables can double-count steps. | Add **RULE: per-member-per-day activity is deduplicated across sources before aggregation (one canonical steps figure/day)**. | Med |
| **GAP-F18** | No **non-wearable earning path / equity** rule. Steps & Sleep (RULE-316) are device-only goals. | Members without a wearable cannot earn the core goals — inequitable for a public-health scheme meant to be inclusive. | Add **BR: an equivalent non-wearable earning path** (e.g. attested check-ins, attended-event credit) so members without devices can reach a comparable WeeklyScore. | High |
| **GAP-F19** | No defined **activity-verification acceptance criteria** behind ACTV-SVC. It is "the trust gate" (invariant 3) without rules for what makes a signal trustworthy (wearable-proxy anti-spoofing). | A named gate with no rules cannot actually gate. | Add **RULE: enumerated validation checks ACTV-SVC applies (source signature, timestamp sanity, range bounds) before emitting `activity.verified`**. | Med |

## F. Challenge Capacity & Enrolment Lifecycle

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F20** | No **enrolment cap / capacity / waitlist**. Enrolment status enum (RULE-010) has no `waitlisted`. | Capacity-limited or partner-budgeted challenges cannot be throttled; over-enrolment can exceed reward funding. | Add **BR: optional challenge capacity with a waitlist and auto-promotion on withdrawal**; extend the enrolment status enum. | Med |
| **GAP-F21** | No **re-enrolment after withdrawal / cool-off**. RULE-009 makes withdrawal irreversible and silently forbids return. | A member who withdraws by accident is permanently locked out of that challenge — a harsh, undocumented UX consequence. | Add **RULE: re-enrolment allowed after a cool-off period with progress reset (or explicitly document permanent lock-out as intended)**. | Med |

## G. Leaderboard / Ranking Fairness

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F22** | No **ranking computation, tie-breaking, or anti-collusion** rules. Leaderboards appear only as a consent-gated consumer (RULE-039). | Undefined ties and collusion (coordinated point-trading) make any public ranking contestable and gameable. | Add **RULE: deterministic leaderboard ranking with explicit tie-break (e.g. earliest-to-reach-score) and anti-collusion detection (clustered identical patterns flagged to FRAUD-SVC)**. | Med |

## H. Consent Withdrawal Mid-Challenge

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F23** | No rule for the **effect of withdrawing a *consent purpose* (vs withdrawing the challenge) mid-challenge** on in-flight scoring and the wallet. RULE-039 only names "leaderboard removal". | Withdrawing activity-processing consent mid-week leaves it undefined whether scoring halts, the wallet freezes, or earned-but-uncredited points are voided — a PDPL and fairness ambiguity. | Add **RULE: consent-purpose withdrawal halts further `activity.verified` ingestion for that member, freezes (does not void) the wallet, and credits already-earned in-period points up to the withdrawal instant; emits `consent.withdrawn.applied`**. | High |

## I. Notifications & Communications

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F24** | No explicit **marketing-vs-transactional consent separation**. RULE-037 has "per-category consent" but neither category is named, so a member could suppress transactional alerts (failed redemption, voucher) or marketing could ride on a transactional channel. | Mis-categorised comms breach consent-marketing rules or hide critical financial notices. | Add **RULE: notifications classified as transactional (always delivered, consent-exempt) vs marketing (consent-required, suppressible)**, mapped onto RULE-037 categories. | Med |
| **GAP-F25** | No **quiet-hours** rule. Frequency budget exists (RULE-036) but no time-of-day suppression. | Night-time pushes to a public-health audience harm trust and may breach local marketing norms. | Add **RULE: marketing/nudge channel respects member quiet-hours (default + override); transactional exempt**. | Low |

## J. Surveys / UGC Integrity

| ID | What's missing | Why it matters (risk) | Recommendation | Severity |
|----|----------------|----------------------|----------------|----------|
| **GAP-F26** | No **content moderation** for any free-text/UGC. Surveys score +1-on-submit and are ungraded (RULE-316), which protects *scoring* integrity but not *content* safety. | If any survey/check-in field accepts free text, unmoderated content (abusive, PII, unsafe health claims) flows into a government platform. | Add **RULE: free-text survey/UGC fields pass moderation (profanity/PII/safety filter) before persistence; offending submissions still score the completion point but quarantine the content**. | Low |

---

### Severity Tally
- **High:** GAP-F01, F02, F03, F05, F08, F10, F12, F13, F15, F16, F18, F23 — 12
- **Med:** GAP-F04, F06, F07, F09, F14, F17, F19, F20, F21, F22, F24 — 11
- **Low:** GAP-F11, F25, F26 — 3
- **Total:** 26
