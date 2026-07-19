# Requirements & Business-Rules Gap Analysis — Recommendations

> Parallel review of the extracted catalogue (114 BR + 139 RULE) for **obvious gaps**. Two passes:
> functional/business-logic and non-functional/compliance. **49 gaps found · 25 High · 21 Med · 3 Low.**
> Detail tables: [`partials/gaps-functional.md`](partials/gaps-functional.md) (26) ·
> [`partials/gaps-nonfunctional.md`](partials/gaps-nonfunctional.md) (23).

## Verdict

The document is **strong on the value path** (scoring engine, wallet ledger, redemption, partner
lifecycle, the OLAP/OLTP seam) and on the invariants that protect *money and reproducibility*. The
gaps cluster in three predictable blind spots for a value-bearing public-health platform: **(1) member-side
identity & protections** (the partner side is rigorously KYB'd, the member side barely proofed),
**(2) the points economy as a regulated financial liability**, and **(3) the NFR/compliance envelope**
(availability, data-protection rights, health-data standards). These are not detail nits — several are
go-live blockers in the UAE regulatory context.

## The 10 material gaps (cross-cutting, High severity)

| # | Theme | Gap | Why it's material | Recommendation |
|---|---|---|---|---|
| 1 | **Member eligibility** | No **age minimum / minor + guardian consent** (F01/F02); eligibility is segment-membership only | A minor can earn redeemable monetary value — UAE age-of-majority + PDPL breach | Add **RULE**: minimum age + verified guardian consent gate at enrolment; model as a **Constraint** on R2 (challenge enrolment) |
| 2 | **Member identity** | No **residency / identity proofing** (F03) — ID-SVC only links/unlinks; member KYC absent (N12) | Duplicate-identity farming of rewards; AML exposure; asymmetry vs rigorous partner KYB | Add **BR**: member identity-proofing level + uniqueness; new **Requirement** "Member Identity Proofing & KYC" realizing G7 (fraud) + G6 (compliance) |
| 3 | **Points as liability** | "Points never expire/reset" (RULE-321) has **no dormancy / breakage / liability-accrual** policy (F08) | Unbounded, unaudited DoH financial liability on the balance sheet | Add **RULE**: liability accrual + breakage/dormancy policy (or explicit board-level "never expire" decision with funding model); **Constraint** on R5 |
| 4 | **Stored-value / AML** | Points economy **unassessed against CBUAE Stored-Value-Facility** rules; no member transaction monitoring / sanctions screening (N11/N12) | A points currency redeemable for real value may be a regulated SVF; AML obligations | Add **Driver** "Financial-services regulatory compliance" + **Requirement** "AML / SVF controls"; legal determination before launch |
| 5 | **Fraud recovery** | No **clawback / negative-balance-on-reversal** rule (F10) | FRAUD-SVC can detect but cannot recover points already earned-and-spent | Add **RULE**: reversal/clawback semantics on the append-only ledger (compensating entries, negative-balance handling); **Constraint** on R5/R12 |
| 6 | **Availability / DR** | No **SLA/SLO, RTO/RPO, DR, backup, multi-AZ** — only latency budgets (N20) | A value-bearing wallet needs RPO≈0; today resilience is unspecified | Add **Outcomes** with availability targets + an NFR **Requirement** "Resilience & DR (RPO≈0 for ledger)" |
| 7 | **PDPL rights** | **Data-subject rights** (access/rectification/erasure/portability/objection) only generically referenced; no erasure model over append-only ledgers (N01) | PDPL non-compliance; erasure-vs-immutability conflict unresolved | Add **Requirement** "PDPL Data-Subject Rights" + a **Principle** reconciling erasure with the immutable ledger (crypto-shredding / tombstoning) |
| 8 | **Health-data standard** | **ADHICS absent**; clinical data not classified special-category (N06/N07) | Mandatory Abu Dhabi health-information & cyber-security standard for CLIN-SVC data | Add **Driver** "ADHICS / health-data compliance" + **Constraint**: special-category handling for clinical signals |
| 9 | **Data residency** | No **residency / cross-border-transfer** controls though global partners (Reloadly/Etisalat) receive PII (N03) | PDPL cross-border breach via the redemption path | Add **Constraint**: data-residency + minimised PII in partner calls; **Principle** "minimal PII to partners" |
| 10 | **Anti-cheat & equity** | No **step-gaming / manual-entry anti-cheat** (F15/F16) and **no non-wearable earning path** (F18) | Rewards are gameable; and members without wearables are excluded (equity/fairness) | Strengthen R3 (verification) with anti-cheat **RULEs**; add **BR**: inclusive non-wearable earning path |

## Secondary gaps worth tracking (High/Med)

- **Member dispute/appeal** (F05) — partners can dispute settlement; members can't contest a score, denied goal, or failed redemption. Add a member-facing dispute Business Process.
- **Week-close boundary** (F12) + **late-arrival grace window** (F13) — the GST timezone of "week close" and handling of late `activity.verified` events are undefined; both directly affect scoring determinism (a reproducibility risk against Principle P1).
- **Consent withdrawal mid-challenge** (F23) — effect on in-flight scoring/wallet undefined (RULE-039 covers only leaderboard cleanup). PDPL ambiguity.
- **Security baseline** — MFA (N15), key-rotation + edge-TLS (N17), audit **non-repudiation / WORM** (N19), pen-test/vuln-mgmt programme, **breach-notification** process (N05).
- **Accessibility & localisation** — WCAG + **Arabic/English bilingual + RTL** (N24): a UAE government digital-service requirement, entirely absent.
- **Challenge capacity / waitlist / re-enrolment cool-off** (F-series), **rate-limiting / DDoS at the edge**, **single-partner business-continuity fallback**.

## How this feeds the ArchiMate model

These recommendations are **additive** to the Motivation layer already built in
`motivation-strategy.archimate.xml`. The concrete next-cut edits:

- **+2 Drivers**: "Financial-services regulatory compliance", "ADHICS / health-data compliance".
- **+4 Requirements**: Member Identity Proofing & KYC · AML/SVF Controls · PDPL Data-Subject Rights · Resilience & DR.
- **+~8 Constraints**: age/guardian gate · points-liability/breakage · fraud clawback · data-residency · special-category clinical handling · GST week-boundary · MFA · WORM audit.
- **+2 Principles**: "minimal PII to partners", "erasure reconciled with the immutable ledger".

Each new element keeps the same relationship scheme (Constraint ─realize→ Goal, ─influence(−)→ Requirement;
Driver ─influence→ Goal). Once you confirm these, I can regenerate the XML with them folded in.

## Recommendation

Treat gaps **#1–#9** as **go-live blockers** for a UAE value-bearing health platform (legal/regulatory),
and **#10 + the secondary set** as fast-follows. Suggest a short decision session on three items that need a
*business* answer, not an architectural one: the points-expiry/liability stance (#3), the stored-value/AML
legal determination (#4), and the erasure-vs-immutable-ledger reconciliation (#7).
