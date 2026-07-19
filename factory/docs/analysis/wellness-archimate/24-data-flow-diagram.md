# Data Flow Diagram — Wellness Platform (with Data-Analyst hotspots)

> Built from `solution-architecture-elk.drawio` (components/stores) + `19-behaviour-detailed-sequences.md`
> (flows). DFD notation: **rounded = process**, **cylinder = data store**, **plain rect = external
> entity**, **arrow = data flow (labelled with the data)**. Render the fenced block in https://mermaid.live.
>
> **Colour key — where a Data Analyst is needed**
> - 🟢 **GREEN = definite** — the work *is* an analytical/feature query or aggregation; a data analyst owns the logic.
> - 🟠 **ORANGE = optional** — currently a microservice, but the computation is set-based and **could be pushed
>   to the database / stream-SQL (Lenses) / a materialised view** — an analyst could own it instead.
> - ⚪ Uncoloured = transactional / orchestration / I-O; no analyst needed.

```mermaid
flowchart TB
  %% ---------- external entities ----------
  DOH[DoH]:::ext
  CLIN[Clinical Team]:::ext
  MEM[Member]:::ext
  ADM[Admin]:::ext
  PRT[Partner]:::ext
  PROV[Reward Providers]:::ext
  MAL[Malaffi HIE - clinical membership]:::ext
  SAH[Sahatna - app renderer + Notifications]:::ext

  %% ---------- data stores ----------
  D1[(D1 Feature store<br/>demographic + telemetry features)]:::astore
  D2[(D2 Segment / Cohort store<br/>segment_id + local membership)]:::astore
  D4[(D4 Challenge + ScoringPlan<br/>frozen definition + localized content AR/EN)]
  D6[(D6 Event Hub<br/>versioned event spine)]
  D7[(D7 Score / Progress store)]
  D8[(D8 Wallet ledger<br/>balance, txn, reservation)]
  D9[(D9 Marketplace store<br/>item, redemption, voucher)]
  D10[(D10 Warehouse / OLAP<br/>DATA-SVC)]:::astore
  D11[(D11 Consent store<br/>CONS-SVC · notify-consent + channels)]

  %% ---------- processes ----------
  P1(P1 Define Features)
  P2(P2 Build Local Segment / Cohort):::analyst
  P4(P4 Author + Freeze Challenge)
  P5(P5 Eligibility Resolve):::optional
  P6(P6 Enrol / Subscribe)
  P7(P7 Ingest Telemetry)
  P8(P8 Verify + Normalise):::optional
  P9(P9 Score + Recognise<br/>daily / weekly / streak):::optional
  P10(P10 Credit Wallet Ledger)
  P11(P11 Redeem Saga<br/>reserve to fraud to partner)
  P12(P12 Inline Fraud Guard<br/>sync, before value transfer)
  P13(P13 Async Anomaly / Fraud):::analyst
  P14(P14 Leaderboard / Standings):::optional
  P15(P15 Settlement Aggregate + Reconcile):::analyst
  P16(P16 Analytics / Dashboards):::analyst
  P17(P17 Notify)

  %% ===== Precondition: features -> segments =====
  DOH -->|feature defs| P1 -->|features| D1
  MEM -->|demographic profile| D1
  P7 -->|telemetry features| D1
  D1 -->|FEATURE QUERY| P2 -->|segment_id + membership| D2
  CLIN -->|build clinical segment| MAL

  %% ===== Design-time: author + freeze =====
  ADM -->|author challenge| P4
  P4 -->|segment metadata, no membership| MAL
  ADM -->|author localized content AR/EN| P4
  P4 -->|freeze definition + localized content| D4
  P4 -->|challenge.published| D6

  %% ===== Runtime: eligibility =====
  MEM -->|which challenges eligible| P5
  P5 -->|active segment_ids| D2
  P5 -->|scoped membership query| MAL
  P5 -->|map segments to challenge_ids| D4
  P5 -->|read localized published content| D4
  P5 -->|localized published challenges| SAH

  %% ===== Runtime: enrol (subscription armed OFF the event hub, not written by the enrol step) =====
  MEM -->|enrol, accept T&C| P6
  P6 -->|record notify-consent + channels| D11
  P6 -->|enrolment.created| D6
  D6 -->|arm: init scoring state from frozen ScoringPlan| P9
  P9 -->|init subscription scoring state| D7

  %% ===== Earn loop =====
  MEM -->|wearable telemetry| P7 -->|telemetry.ingest| D6
  D6 -->|telemetry| P8 -->|activity.verified| D6
  D6 -->|activity.verified| P9
  P9 -->|read frozen ScoringPlan| D4
  P9 -->|score + streak| D7
  P9 -->|WeeklyScore x10| P10
  P10 -->|append ledger| D8
  P10 -->|points.credited| D6

  %% ===== Leaderboard =====
  D7 -->|participant scores| P14 -->|rankings| MEM
  P14 -->|final standings + winners, off-platform| DOH

  %% ===== Redeem =====
  MEM -->|redeem, Idempotency-Key| P11
  P11 -->|reserve points 300s| D8
  P11 -->|inline fraud check, sync| P12
  P12 -->|clear / flagged| P11
  P11 -->|call Partner API, if clear| PROV
  P11 -->|confirm debit / release reservation| D8
  P11 -->|voucher + redemption| D9
  P11 -->|voucher.issued / redemption.uncertain| D6

  %% ===== Async consumers + analytics =====
  D6 -->|points + redemption events| P13 -->|anomaly signals| D10
  D6 -->|all events| D10
  D8 -->|ledger| P15
  D9 -->|redemptions| P15
  P15 -->|aggregate per partner| D10
  P15 -->|VAT invoice + IBAN payout| DOH
  P15 -->|pay partner, 5pct holdback, release 30d| PRT
  D10 -->|datasets| P16 -->|dashboards| ADM

  %% ===== Notifications =====
  P9 -->|streak at risk| P17
  P11 -->|voucher issued| P17
  D11 -->|check notify-consent| P17
  P17 -->|consent-checked request, only if granted| SAH -->|push / email / SMS| MEM

  classDef analyst fill:#D5E8D4,stroke:#2E7D32,stroke-width:2px,color:#1b5e20;
  classDef optional fill:#FFE6CC,stroke:#E07B00,stroke-width:2px,color:#7a3e00;
  classDef astore fill:#EAF7EA,stroke:#2E7D32,stroke-width:1.5px,color:#1b5e20;
  classDef ext fill:#F5F5F5,stroke:#888,color:#333;
```

## Data-Analyst hotspots

### 🟢 Definite (analyst owns the logic)
| # | Process / Store | Why it is analytical | Data involved |
|---|---|---|---|
| **P2** | **Build Local Segment / Cohort** | The canonical case: a **feature query** (`WHERE` over demographic + telemetry features) materialises `segment_id` + membership. Segment definition = SQL/feature logic. | D1 Feature store → D2 Segment store |
| **P13** | Async Anomaly / Fraud | Velocity / duplicate / outlier detection over the event stream — statistical, threshold-tuned (analyst/▸data scientist). | D6 events → D10 |
| **P15** | Settlement aggregate + reconcile | `SUM` redemptions per partner, reconcile vs ledger, **>0.1% variance flag** — pure aggregation/reconciliation query. | D8 + D9 → D10 |
| **P16** | Analytics / Dashboards (DATA-SVC) | Warehouse/OLAP models, KPIs, sponsor reporting. | D10 |
| D1 / D2 / D10 | Feature store · Segment store · Warehouse | Analyst-owned data assets (feature engineering, segment SQL, OLAP models). | — |

### 🟠 Optional (could move from microservice to DB / stream-SQL / materialised view)
| # | Process | Today | Analyst alternative |
|---|---|---|---|
| **P9** | **Score + Recognise** (earn loop) | Scoring/streak logic in the microservice | **Push to stream-SQL (Lenses) or DB window functions** — daily/weekly aggregation + streak run as set-based queries; inv-3 verify-gate stays upstream. *Your example.* |
| **P8** | Verify + Normalise | Microservice validation | Stream-SQL normalise/validate on the telemetry topic. |
| **P5** | Eligibility Resolve | Service maps segments→challenge_ids per request (inv-1 <50ms) | **Materialised view** `member × eligible_challenge_id`, analyst-maintained, refreshed on segment/binding change — keeps the seam fast. |
| **P14** | Leaderboard / Standings | Service ranks participants | Ranking is a **window query** (`RANK() OVER`) — natural DB/OLAP job, materialised per challenge. |
| (P10) | Wallet lifetime/balance stats | Ledger fold in service | Lifetime/earned aggregates as a materialised rollup (light). |

## Notes
- Flow labels are the *data*, not calls; events via **D6 Event Hub** are async (the spine, inv-6).
- Clinical membership stays **external on Malaffi** (P5 scoped query) — not an analyst asset here.
- The 🟢 chain D1→P2→D2 is the "cohort creation = query involving features" you called out; the 🟠
  P8/P9 chain is the "scoring could be done in the database" you called out — both highlighted in place.
```
