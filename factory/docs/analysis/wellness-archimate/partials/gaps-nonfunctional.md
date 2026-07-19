# Non-Functional, Compliance, Security & Operational Gaps

Catalogue reviewed: `00-business-requirements-and-rules.md` + `partials/part-1..4.md` (BR-xxx / RULE-xxx).
Context: UAE (Abu Dhabi / ADPHC–DoH) public-health reward platform. Health/clinical data + a Sahatna-Points economy redeemable for real monetary value.

## Executive Summary — most material / regulatory gaps

- **No availability, DR or resilience targets exist at all.** The catalogue specifies tight latency budgets (RULE-204/205/006) but defines no uptime SLA/SLO, RTO, RPO, backup, multi-AZ or DR posture. For a government-sponsored health + value-bearing platform this is the single largest non-functional hole. (GAP-N20, High)
- **PDPL data-subject rights are only generically referenced**, not enumerated. UAE PDPL (Federal Decree-Law 45/2021) grants access, rectification, erasure, portability, objection and automated-decision rights; only a generic "fulfil subject-rights requests" (BR-029) exists, and no member-level erasure honouring the append-only ledgers. (GAP-N01, High)
- **No data-residency or cross-border-transfer controls** despite global partner adapters (Reloadly global, Etisalat, YouGotaGift). PDPL Arts. 22–23 restrict transfer of personal data outside the UAE; nothing governs PII leaving the country. (GAP-N03, High)
- **Health-data regime is incomplete.** Clinical sources (IFHAS/Malaffi/Riayati/Nabidh) are named but ADHICS (Abu Dhabi Healthcare Information & Cyber Security standard) — mandatory for any Abu Dhabi entity handling health information — is entirely absent, as is special-category-data classification. (GAP-N06, High)
- **The points economy is not assessed as stored value.** Points convert to real value (RULE-318/319) and redeem for vouchers, yet there is no member-side KYC, no transaction monitoring, no sanctions screening of redeemers, and no CBUAE Stored-Value-Facility regulatory determination. AML controls are partner-onboarding (KYB) only. (GAP-N11/N12, High)
- **Core security primitives are unstated**: no MFA, no key-rotation schedule, no explicit TLS/encryption-in-transit standard for citizen traffic, no pen-test / vulnerability-management programme, and audit immutability is only "append-only" (not tamper-evident/WORM/non-repudiation). (GAP-N15/N16/N17/N19, High)

---

## Gaps by Domain

### A. Data Protection / PDPL

| ID | Domain | What's missing | Regulatory / risk driver | Recommendation (BR/RULE or control to add) | Severity |
|----|--------|----------------|--------------------------|--------------------------------------------|----------|
| GAP-N01 | PDPL rights | The six data-subject rights are not enumerated; only generic BR-029 "fulfil subject-rights requests". | PDPL Arts. 13–19 (access, rectification, erasure, restriction, portability, objection). | Add BR enumerating each right with an SLA (e.g. 30 days), and RULE: erasure produces a tombstone over append-only ledgers (pseudonymise rather than physically delete, preserving double-entry integrity). | High |
| GAP-N02 | Automated decisions | Scoring/fraud/eligibility are automated but no right to human review / explanation. | PDPL Art. 19 (automated processing). | Add RULE: FRAUD-SVC and SCORE-SVC decisions affecting points/eligibility are appealable to a human; record rationale. | Med |
| GAP-N03 | Data residency / cross-border | No UAE-hosting mandate; no cross-border-transfer controls despite global partners (Reloadly, Etisalat). | PDPL Arts. 22–23; DoH/government data-residency expectations. | Add BR: personal + clinical data resident in UAE region; RULE: PII to off-UAE partners requires adequacy/SCC + minimised fields (name/phone only) under signed PDPL addendum (extend RULE-226/313). | High |
| GAP-N04 | Retention scope | 7y retention + 2y PII masking (RULE-206) is **partner-data only**; no member-data retention/masking schedule. | PDPL storage-limitation principle. | Add RULE: member-data retention schedule per data class (identity, clinical, wallet, behavioural) with masking/anonymisation timers. | Med |
| GAP-N05 | Breach notification | No breach-detection-to-notification process or timeline. | PDPL Art. 9 (breach notification to UAE Data Office "without undue delay"). | Add BR + runbook: breach severity classification, Data-Office + data-subject notification timelines, evidence capture. | High |

### B. Health / Clinical Data

| ID | Domain | What's missing | Regulatory / risk driver | Recommendation | Severity |
|----|--------|----------------|--------------------------|----------------|----------|
| GAP-N06 | ADHICS | No reference to ADHICS controls; clinical handled like ordinary PII. | ADHICS v2 mandatory for Abu Dhabi health-info entities. | Add BR: platform certified to ADHICS controls; map encryption/access/audit RULEs to ADHICS control families. | High |
| GAP-N07 | Special category | Clinical data not classified as special-category with elevated controls. | PDPL Art. 5 (sensitive personal data) + ADHICS. | Add RULE: CLIN-SVC data tagged sensitive → stricter RBAC, separate KMS keys, mandatory consent + access logging (extend RULE-114). | High |
| GAP-N08 | Malaffi / HIE governance | Malaffi/Riayati/Nabidh named as sources only; no HIE data-sharing agreement, purpose-binding or pull-vs-push governance. | Malaffi participation terms; DoH HIE policy. | Add BR: HIE integration governed by data-sharing agreement; RULE: clinical pulls purpose-bound + audit-logged per member. | Med |

### C. Financial / AML / Stored Value

| ID | Domain | What's missing | Regulatory / risk driver | Recommendation | Severity |
|----|--------|----------------|--------------------------|----------------|----------|
| GAP-N11 | Stored-value determination | Points-as-value (RULE-318/319) not assessed against CBUAE Stored-Value-Facility (SVF) regulation. | CBUAE SVF Regulation 2020 — points redeemable for goods/value may constitute a stored-value facility. | Add BR: obtain regulatory determination (closed-loop reward exemption vs SVF licensing); document position + controls. | High |
| GAP-N12 | Member AML/KYC + monitoring | AML is KYB (partner) only; no member-side KYC, no transaction monitoring, no sanctions screening of redeemers. | UAE AML Federal Decree-Law 20/2018; sanctions (UNSC/UAE local lists). | Add RULE: redemption velocity/value thresholds trigger enhanced checks + sanctions screening of redeemer; SAR/STR escalation path. | High |
| GAP-N13 | Points-economy abuse | Earning/redemption abuse limits beyond voucher re-display (RULE-313) and nudge cap not defined; no anti-collusion/multi-account controls. | Fraud loss; reputational risk to DoH. | Add RULE: per-member daily/weekly points-earning velocity caps + multi-account / device-fingerprint correlation in FRAUD-SVC. | Med |

### D. Security

| ID | Domain | What's missing | Regulatory / risk driver | Recommendation | Severity |
|----|--------|----------------|--------------------------|----------------|----------|
| GAP-N15 | MFA | No multi-factor / step-up auth requirement (ID-SVC = OIDC/JWKS only). | ADHICS access control; account-takeover risk on value-bearing accounts. | Add RULE: MFA via UAE Pass (or step-up) required for high-value redemptions + admin roles. | High |
| GAP-N16 | Key rotation | RULE-225/313 use Key Vault/KMS but no rotation schedule or crypto-period. | ADHICS / ISO 27001 key-management. | Add RULE: KMS keys rotated on a defined crypto-period; column-keys versioned; rotation audit-logged. | Med |
| GAP-N17 | Encryption in transit | mTLS specified internally (RULE-229) but no explicit TLS minimum for citizen edge traffic; no at-rest baseline beyond voucher columns. | ADHICS; PDPL security-of-processing. | Add RULE: TLS 1.2+ for all external traffic; full-disk/DB encryption-at-rest baseline (not just voucher columns). | High |
| GAP-N18 | RBAC/ABAC model | Roles listed (RULE-233) but no permission matrix / least-privilege model. | ADHICS access control. | Add RULE: documented permission matrix per role; deny-by-default; periodic access review. | Med |
| GAP-N19 | Audit immutability / non-repudiation | Ledgers are "append-only" (RULE-018/025) but not tamper-evident; no WORM/hash-chain/non-repudiation. | Evidentiary integrity for value + regulatory audit. | Add RULE: scoring/wallet/redemption audit records hash-chained or WORM-stored; signed for non-repudiation. | High |
| GAP-N20-SEC | Pen-test / vuln-mgmt | No penetration-testing, vulnerability-scanning or secure-SDLC requirement. | ADHICS / NESA-equivalent; supply-chain risk. | Add BR: annual third-party pen-test + continuous dependency/container scanning gate (aligns with repo OWASP/container-scan principle). | High |

### E. Availability / Resilience / Operations

| ID | Domain | What's missing | Regulatory / risk driver | Recommendation | Severity |
|----|--------|----------------|--------------------------|----------------|----------|
| GAP-N20 | SLA/SLO/DR | No uptime target, RTO, RPO, backup, multi-AZ or DR plan (only latency budgets). | Government service-availability expectation; value-bearing wallet must not lose data. | Add BR: uptime SLO (e.g. 99.9%), RTO/RPO targets, backup cadence, multi-AZ + DR runbook; wallet ledger RPO ≈ 0. | High |
| GAP-N21 | Observability depth | trace_id + divergence alerts exist (RULE-030/301) but no SLI/SLO defs, alert thresholds, on-call or incident process. | Operability; mean-time-to-detect for value/clinical incidents. | Add BR: SLI/SLO catalogue, golden-signal alerting thresholds, on-call rota + incident-management process. | Med |
| GAP-N22 | Edge rate-limiting / DDoS / WAF | No API-edge rate-limiting, DDoS or WAF requirement (only voucher re-display + nudge caps). | Availability + abuse protection at public edge. | Add RULE: APIM-level rate limits per token/IP, WAF, and DDoS protection on the citizen edge. | Med |
| GAP-N23 | Partner business continuity | Routing fallback (RULE-311/232) exists, but "uncertain" cases go manual; no single-partner-outage BC plan or value-source diversification SLA. | Redemption continuity; member trust. | Add RULE: per-category minimum of 2 live sourcing partners; documented partner-outage BC procedure + ops escalation SLA. | Med |

### F. Accessibility / Localisation

| ID | Domain | What's missing | Regulatory / risk driver | Recommendation | Severity |
|----|--------|----------------|--------------------------|----------------|----------|
| GAP-N24 | WCAG accessibility | No accessibility standard; only voucher `locale ∈ {en,ar}` (RULE-306). | UAE government digital-service accessibility mandate; inclusion. | Add BR: UI conforms to WCAG 2.1 AA. | High |
| GAP-N25 | Bilingual + RTL | No bilingual-UI or RTL requirement (only voucher locale enum). | UAE government bilingual (Arabic/English) + RTL requirement. | Add BR: full Arabic/English bilingual UI with RTL layout support. | Med |

---

## Severity totals

- **High:** GAP-N01, N03, N05, N06, N07, N11, N12, N15, N17, N19, N20, N20-SEC, N24 = **13**
- **Med:** GAP-N02, N04, N08, N13, N16, N18, N21, N22, N23, N25 = **10**
- **Low:** 0
- **Total gaps: 23**
