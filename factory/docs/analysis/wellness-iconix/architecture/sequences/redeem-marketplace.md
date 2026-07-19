# Application-Level Sequences — Redeem & Marketplace (`redeem-marketplace`) 🟢 P1

**Altitude**: Top-down solution structure, abstracted UP from the bottom-up ICONIX low-level sequences in [`../../04-sequences/redeem-marketplace.md`](../../04-sequences/redeem-marketplace.md). Participants are **applications, microservices, datastores, and external systems** — not robustness controllers or fine-grained messages. Each low-level controller chain collapses into a coarse application-to-application call.

**Bounded context**: Rewards, Wallet & Marketplace → **rewards-svc** [stores: `points-ledger` (append-only), `marketplace-db` (PostgreSQL), `reward-image-store` (object storage)]. Cross-context collaborators: scoring-svc, recognition-svc, ingestion-svc, settlement-svc, notification-svc, reporting-svc.

**Phase scope**: All journeys P1, gated behind the **points feature flag** (BRD: points suppressed for the Sept-2026 launch). No Team/District/Title/baseline concepts → no P2/P3 fragments.

**Flag convention**: every points-bearing journey is wrapped by a `pointsFeatureFlag` gate inside rewards-svc; shown once per diagram rather than per call.

---

## Journey 1 — Accrue Reward Points (covers UC-G1)

Triggered asynchronously when a week is finalized (scoring/settlement). rewards-svc credits the wallet ledger and rolls in bonus points sourced from recognition (winner), Sahatna events, and IFHAS screening — all reached as cross-context reads, not local data.

```mermaid
sequenceDiagram
    autonumber
    participant SCO as scoring-svc
    participant SET as settlement-svc
    participant RW as 🟦 rewards-svc
    participant LED as points-ledger
    participant REC as recognition-svc
        participant SAH as Sahatna Events
        participant IFH as IFHAS Screening
    participant NTF as notification-svc

    SCO-->>RW: async WeekFinalizedEvent(enrollmentId, weekId)
    SET-->>RW: async WinnerSettledEvent(enrollmentId)
    Note over RW: pointsFeatureFlag gate — OFF ⇒ suppress accrual (G1.4)

    RW->>SCO: getWeeklyScore(weekId)
    RW->>RW: idempotency + weekly-cap (G1.1/G1.2/G1.3)
    RW->>LED: append earn txn (points = score × 10, capped)

    RW->>REC: getWinnerBonus(enrollmentId)
    RW->>SAH: getEventBonus(signup, checkin)
    RW->>IFH: getScreeningBonus(IFHAS)
    RW->>LED: append earn txn (bonus points)

    RW-->>NTF: async PointsAccruedEvent(memberId, total)
```

> 🟥 svc receives from outside GP · 🟦 svc writes to outside GP (microservices only)

> **Trace**: covers **UC-G1** (Accrue Reward Points), alt-courses G1.1–G1.4. Flag gate, once-per-week guard, weekly cap, and bonus crediting all collapse into rewards-svc + cross-context bonus reads (recognition/Sahatna/IFHAS); ledger writes land in `points-ledger`.

---

## Journey 2 — View Wallet & My Rewards (covers UC-G2, UC-G5)

Two read-only member journeys merged: the points wallet/history and the issued reward artifacts. Both are reads against rewards-svc stores; artifact code/QR images come from `reward-image-store`.

```mermaid
sequenceDiagram
    autonumber
    actor Member
        participant APP as Mobile App
        participant APN as APIM-north (Citizen Gateway)
        participant BFF as Mobile BFF
        participant APS as APIM-south (Platform Gateway)
    participant RW as 🟥 rewards-svc
    participant LED as points-ledger
    participant MKT as marketplace-db
    participant IMG as reward-image-store

    Member->>APP: open Wallet / My Rewards
    APP->>APN: GET wallet + rewards (memberId, UAE Pass JWT)
    APN->>BFF: getWalletView(memberId)
    BFF->>APS: getWalletView(memberId)
    APS->>RW: getWalletView(memberId)

    RW->>LED: read balances + transaction history
    RW->>MKT: list redemptions + voucher state
    RW->>RW: evaluate usable vs expired/used (G5.1)
    RW->>IMG: fetch artifact code/QR payload
    RW-->>BFF: WalletView + MyRewards (balances, history, artifacts)
    BFF-->>APP: composed wallet response
    APP-->>Member: render wallet, history, redeemable artifacts
```

> **Trace**: covers **UC-G2** (View Wallet) and **UC-G5** (My Rewards / Artifact). Empty-history and expired/used artifact alternates handled inside rewards-svc; balances/history from `points-ledger`, redemptions from `marketplace-db`, code/QR from `reward-image-store`.

---

## Journey 3 — Browse Catalog & Redeem Reward (covers UC-G3, UC-G4)

The transactional heart. Browse computes affordability and live stock; redeem is an atomic rewards-svc transaction (validate balance → enforce per-user limit → reserve stock → apply discount → debit ledger → issue voucher → persist redemption). All inventory/discount/voucher logic is internal to rewards-svc across `points-ledger` + `marketplace-db`.

```mermaid
sequenceDiagram
    autonumber
    actor Member
        participant APP as Mobile App
        participant APN as APIM-north (Citizen Gateway)
        participant BFF as Mobile BFF
        participant APS as APIM-south (Platform Gateway)
    participant RW as 🟥 rewards-svc
    participant MKT as marketplace-db
    participant LED as points-ledger
    participant IMG as reward-image-store
    participant NTF as notification-svc

    Member->>APP: open catalog / reward detail
    APP->>APN: GET catalog (memberId, UAE Pass JWT)
    APN->>BFF: browse(memberId)
    BFF->>APS: browse(memberId)
    APS->>RW: browse(memberId)
    Note over RW: pointsFeatureFlag gate — OFF ⇒ catalog hidden (G3)
    RW->>MKT: list items + per-item stock
    RW->>LED: read balance → "points needed" / Out-of-Stock (G3.1)
    RW->>IMG: fetch item images
    RW-->>BFF: catalog (prices, affordability, stock, images)
    BFF-->>APP: composed catalog

    Member->>APP: confirm redeem(itemId)
    APP->>APN: POST redeem(memberId, itemId, UAE Pass JWT)
    APN->>BFF: redeem(memberId, itemId)
    BFF->>APS: redeem(memberId, itemId)
    APS->>RW: redeem(memberId, itemId)
    RW->>MKT: TX — reserve stock + apply discount (G4.2/G4.3/G4.4)
    RW->>LED: TX — debit points + append redeem txn (G4.1)
    RW->>MKT: TX — issue voucher + persist redemption (status ISSUED)
    RW-->>NTF: async RedemptionIssuedEvent(memberId, voucher)
    RW-->>BFF: REDEMPTION_OK(voucher code/QR, expiry)
    BFF-->>APP: redemption result (artifact)
    APP-->>Member: show artifact (valid-until)
```

> **Trace**: covers **UC-G3** (Browse Catalog) and **UC-G4** (Redeem Reward, transactional). Flag gate, insufficient-balance (G4.1), per-user limit (G4.2), out-of-stock (G4.3), and discount-type branch (G4.4) collapse into a single atomic rewards-svc transaction spanning `marketplace-db` (inventory/voucher/redemption) and `points-ledger` (debit). Async event hands off delivery to notification-svc (downstream of consent gate).

---

## Journey 4 — Configure Catalog & Submit Reward (covers UC-G6, UC-G7)

Admin/partner authoring journeys merged. Partner submission and DoH/ADHDS staff configuration both upsert items into `marketplace-db` and initialize inventory. For the September Challenge the **reward image is handed manually to the Malaffi team** (offline ACL, no upload UI) and later linked into `reward-image-store`.

```mermaid
sequenceDiagram
    autonumber
    actor Staff as DoH / ADHDS Staff
    actor Partner as Reward Partner
        participant ADM as Admin Portal (DoH/ADHDS)
        participant APS as APIM-south (Platform Gateway)
    participant RW as rewards-svc
    participant MKT as marketplace-db
    %% Malaffi is canonically an OUTGOING (clinical-query/settlement) external; in THIS diagram it stages the reward image INTO GP's reward-image-store, so dominant direction here is incoming → GP
        participant MAL as Malaffi / DoH-ADHDS
    participant IMG as reward-image-store

    Partner->>MAL: hand reward image (offline, manual) (G7.1)
    MAL-->>IMG: stage reward image (manual intake ACL)
    Note over MAL,IMG: CMS-managed upload is a later increment (G7.2)

    Partner->>ADM: submit reward (discount type+amount, limits)
    Staff->>ADM: configure / review catalog item (add/edit/remove)
    ADM->>APS: applyConfig(itemDraft, Entra SSO)
    APS->>RW: applyConfig(itemDraft, action)
    RW->>RW: validate cost/validity/limits + discount pair (G6 / G7.3)
    RW->>MKT: upsert MarketplaceItem + init inventory counters
    RW->>IMG: link staged reward image
    RW-->>ADM: CONFIG_SAVED / REWARD_SUBMITTED(itemId)
    ADM-->>Staff: confirm saved
    ADM-->>Partner: confirm submitted
```

> **Trace**: covers **UC-G6** (Configure Catalog & Inventory) and **UC-G7** (Submit Reward, marketplace supplement). Validation (G6), manual Malaffi image intake (G7.1), deferred CMS upload (G7.2), and discount-pair check (G7.3) all resolve inside rewards-svc; items + inventory persist to `marketplace-db`, images to `reward-image-store` via the Malaffi manual-intake ACL.

---

## Cross-context call & event summary

| From | To | Kind | Journey |
|---|---|---|---|
| scoring-svc / settlement-svc | rewards-svc | async event (WeekFinalized / WinnerSettled) | J1 |
| rewards-svc | scoring-svc | sync read (weekly score) | J1 |
| rewards-svc | recognition-svc / Sahatna / IFHAS | sync read (bonus points) | J1 |
| rewards-svc | notification-svc | async event (PointsAccrued / RedemptionIssued) | J1, J3 |
| Mobile App → APIM-north → Mobile BFF → APIM-south | rewards-svc | sync request (citizen path) | J2, J3 |
| Admin Portal → APIM-south | rewards-svc | sync request (staff path, Entra SSO, no BFF) | J4 |
| Reward Partner / Malaffi | reward-image-store | manual offline ACL intake | J4 |

**Invariant check (application layer)**
- ✅ Participants are only apps, microservices, datastores, external systems — zero robustness controllers leaked.
- ✅ All redeem-marketplace data ownership stays inside **rewards-svc** stores; cross-context needs (score, bonus, delivery) are explicit sync reads or async events.
- ✅ Each diagram ≤ ~15 messages; trivial UCs merged (G2+G5 reads; G3+G4 catalog/redeem; G6+G7 authoring).
- ✅ Every covering UC (G1–G7) mapped; feature-flag gate retained on points-bearing journeys (J1, J3); no P2/P3 messages.
