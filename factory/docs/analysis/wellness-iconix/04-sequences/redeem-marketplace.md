# ICONIX Step 3 — Sequence Diagrams

## Package G — Redeem / Marketplace (`redeem-marketplace`)  🟢 P1 (feature-flagged)

**Process**: ICONIX (Rosenberg) — Sequence diagrams (the third leg: use case → robustness → **sequence**). The robustness diagram's **controllers became the messages/methods**; each operation is **allocated to the entity that owns the data** it touches. Boundary objects appear as participants; the actor talks only to boundaries; controllers appear as orchestrating participants and the operation arrows they send.

**Source robustness**: `03-robustness/redeem-marketplace.md` (UC-G1…UC-G6).
**Source domain model**: `02-domain-model.md` — entities Member, Wallet, PointTransaction, MarketplaceItem, Redemption, Voucher, WeeklyScore, SahatnaEvent, Screening + ★new analysis entities RewardCatalog, RewardArtifact, InventoryRecord (back-propagation pending).

**Scope**: All six use cases are Phase-1 (`🟢 P1`), gated behind the **points feature flag** (BRD: points suppressed for the Sept-2026 launch). No Team/District/Title/baseline-goal concepts appear — so **no P2/P3 fragments** in this package.

**Allocation principle (operation → owning entity)**: e.g. `currentBalance`/`lifetimeEarned`/`lifetimeRedeemed` live on **Wallet** → balance/credit/debit operations are messages **to Wallet**; live stock count lives on **InventoryRecord** → read/decrement messages go **to InventoryRecord** (via `InventoryManager`); expiry lives on **RewardArtifact/Voucher** → expiry checks read it there.

> **Traceability convention**: every message is suffixed/noted with its originating **use-case step id** (e.g. `[G4.1]`), giving backward traceability sequence → robustness alt-course → use case. A per-diagram backward-trace table closes the loop.

---

## UC-G1 — Accrue Reward Points 🟢 P1 (feature-flagged)

*Trigger actor*: **Clock / Scheduler** (time-actor; fires on week finalization ← UC-D5). Boundary is the event `WeeklyFinalizedEvent`.
*Basic Course*: on week finalization, gate the flag → compute `points = weeklyScore × 10` → once-per-week idempotency → weekly cap → credit Wallet + write earn PointTransaction → credit bonus (winner/event/screening) points.
*Alternate Courses*: G1.4 flag OFF (suppress accrual); G1.1 already credited this week (stop); G1.2 retroactive score change (idempotent — no re-credit); G1.3 cap exceeded (clamp).

```mermaid
sequenceDiagram
    autonumber
    actor Clock as Clock / Scheduler
    participant EV as «B» WeeklyFinalizedEvent
    participant Gate as «C» PointsFeatureFlagGate
    participant Acc as «C» RewardAccrualController
    participant Once as «C» OncePerWeekGuard
    participant Cap as «C» WeeklyCapEnforcer
    participant Bon as «C» BonusPointsCrediter
    participant WS as «E» WeeklyScore
    participant W as «E» Wallet
    participant PT as «E» PointTransaction
    participant Sahatna as «E» SahatnaEvent
    participant Scr as «E» Screening

    Clock->>EV: weekFinalized(enrollmentId, weekId)
    EV->>Gate: onWeekFinalized(weekId)

    alt G1.4 pointsFeatureFlag OFF
        Gate-->>EV: suppressAccrual()  %% [G1.4]
    else flag ON
        Gate->>Acc: accrue(enrollmentId, weekId)

        Acc->>WS: getScoreValue(weekId)
        WS-->>Acc: scoreValue(0..100)

        Acc->>Once: assertNotYetCredited(weekId)
        alt G1.1 already credited this week
            Once-->>Acc: alreadyCredited(weekId) → stop  %% [G1.1] [G1.2 retroactive = idempotent no-op]
        else first credit for week
            Acc->>Cap: clampToWeeklyCap(scoreValue * 10)
            Cap-->>Acc: cappedPoints (≤ scoreValue*10)  %% [G1.3]

            Acc->>W: credit(cappedPoints)
            W->>W: currentBalance += cappedPoints, lifetimeEarned += cappedPoints
            Acc->>PT: record(type=earn, points=cappedPoints, weekIdentifier=weekId)

            Acc->>Bon: creditBonus(enrollmentId, weekId)
            Bon->>Sahatna: getEarnedPoints(signup, checkin)
            Sahatna-->>Bon: eventPoints
            Bon->>Scr: getEarnedPoints(IFHAS)
            Scr-->>Bon: screeningPoints
            Bon->>W: credit(eventPoints + screeningPoints)
            Bon->>PT: record(type=earn, sourceRef=event/screening)
        end
    end
```

**Backward traceability (UC-G1)**

| Message | Robustness object | Use-case step |
|---|---|---|
| `onWeekFinalized` / `suppressAccrual` | PointsFeatureFlagGate | G1.4 |
| `getScoreValue` | WeeklyScore (entity owns scoreValue) | G1 basic |
| `assertNotYetCredited` / `alreadyCredited` | OncePerWeekGuard | G1.1, G1.2 (idempotent) |
| `clampToWeeklyCap` | WeeklyCapEnforcer | G1.3 |
| `credit` / `currentBalance +=` | Wallet (owns balance) | G1 basic |
| `record(type=earn…)` | PointTransaction (owns ledger row) | G1 basic / audit |
| `creditBonus` + Sahatna/Scr reads | BonusPointsCrediter → SahatnaEvent, Screening | G1 bonus (winner/event/screening) |

---

## UC-G2 — View Reward Points Wallet 🟢 P1

*Actor*: **Participant**. *Basic Course*: open WalletScreen → resolve wallet ownership via Member → read balance + lifetime earned/redeemed from Wallet → assemble transaction history from PointTransaction → render.
*Alternate Course*: empty history (no transactions yet → show empty-state).

```mermaid
sequenceDiagram
    autonumber
    actor P as Participant
    participant WV as «B» WalletScreen
    participant Ctl as «C» WalletViewController
    participant Hist as «C» TransactionHistoryAssembler
    participant M as «E» Member
    participant W as «E» Wallet
    participant PT as «E» PointTransaction

    P->>WV: openWallet()
    WV->>Ctl: getWalletView(memberId)

    Ctl->>M: resolveWallet(memberId)
    M-->>Ctl: walletId

    Ctl->>W: getBalances(walletId)
    W-->>Ctl: currentBalance, lifetimeEarned, lifetimeRedeemed

    Ctl->>Hist: assembleHistory(walletId)
    Hist->>PT: listByWallet(walletId)
    alt empty history
        PT-->>Hist: []  %% no transactions yet
        Hist-->>Ctl: emptyHistory
    else has transactions
        PT-->>Hist: [PointTransaction...]
        Hist-->>Ctl: orderedHistory(by timestamp desc)
    end

    Ctl-->>WV: WalletViewModel(balances, history)
    WV-->>P: render(balance, earned, redeemed, history)
```

**Backward traceability (UC-G2)**

| Message | Robustness object | Use-case step |
|---|---|---|
| `getWalletView` | WalletViewController | G2 basic |
| `resolveWallet` | Member (owns membership→wallet link) | G2 ownership |
| `getBalances` | Wallet (owns balances) | G2 basic |
| `assembleHistory` / `listByWallet` | TransactionHistoryAssembler → PointTransaction | G2 history |

---

## UC-G3 — Browse Marketplace Catalog 🟢 P1 (feature-flagged)

*Actor*: **Participant**. *Basic Course*: open catalog → flag gate → list items from RewardCatalog → compute "points needed" per locked item against Wallet balance → resolve live availability per item from InventoryRecord → flag popular → render.
*Alternate Courses*: G3.1 stock = 0 → "Out of Stock", redeem disabled; flag OFF → catalog hidden/points suppressed.

```mermaid
sequenceDiagram
    autonumber
    actor P as Participant
    participant CS as «B» MarketplaceCatalogScreen
    participant Gate as «C» PointsFeatureFlagGate
    participant Ctl as «C» CatalogBrowseController
    participant Need as «C» PointsNeededCalculator
    participant Inv as «C» InventoryManager
    participant Cat as «E» RewardCatalog ★new
    participant MI as «E» MarketplaceItem
    participant IR as «E» InventoryRecord ★new
    participant W as «E» Wallet

    P->>CS: openCatalog()
    CS->>Gate: gate(memberId)

    alt pointsFeatureFlag OFF
        Gate-->>CS: pointsSuppressed()  %% catalog hidden / no point prices
    else flag ON
        Gate->>Ctl: browse(memberId)

        Ctl->>Cat: listItems()
        Cat->>MI: getItems()
        MI-->>Cat: [MarketplaceItem...]
        Cat-->>Ctl: items + popularHighlights

        loop per item
            Ctl->>Need: pointsNeeded(item.pointCost, memberId)
            Need->>W: getCurrentBalance(memberId)
            W-->>Need: currentBalance
            Need-->>Ctl: needed = max(0, pointCost - currentBalance)

            Ctl->>Inv: availability(item.itemId)
            Inv->>IR: getStock(itemId)
            IR-->>Inv: stockCount
            alt G3.1 stockCount == 0
                Inv-->>Ctl: OUT_OF_STOCK (redeem disabled)  %% [G3.1]
            else in stock
                Inv-->>Ctl: AVAILABLE
            end
        end

        Ctl-->>CS: CatalogViewModel(items, needed, availability, popular)
        CS-->>P: render(catalog, "points needed", Out-of-Stock states)
    end
```

**Backward traceability (UC-G3)**

| Message | Robustness object | Use-case step |
|---|---|---|
| `gate` / `pointsSuppressed` | PointsFeatureFlagGate | G3 flag gate |
| `listItems` / `getItems` / `popularHighlights` | CatalogBrowseController → RewardCatalog → MarketplaceItem | G3 basic |
| `pointsNeeded` / `getCurrentBalance` | PointsNeededCalculator → Wallet | G3 affordability |
| `availability` / `getStock` / `OUT_OF_STOCK` | InventoryManager → InventoryRecord | G3.1 |

---

## UC-G4 — Redeem Reward 🟢 P1 (feature-flagged) — transactional heart

*Actor*: **Participant**. *Basic Course*: open reward detail → confirm → flag gate → validate points balance → enforce per-user redemption limit → **reserve** stock against the total-inventory limit → apply discount (branch by type) → **atomically** deduct points (Wallet + redeem PointTransaction), **issue** the reserved stock (InventoryCounters reserved→issued), issue Voucher with post-redemption expiry, persist Redemption linking them → return voucher.
*Alternate Courses*: G4.1 insufficient balance → prevent; G4.2 per-user redemption limit reached → block; G4.3 out of stock at confirm (remaining=0 under totalInventoryLimit) → block; G4.4 discount-type branch PERCENTAGE vs CURRENCY_AMOUNT; flag OFF → redemption disabled.

```mermaid
sequenceDiagram
    autonumber
    actor P as Participant
    participant RD as «B» RewardDetailScreen
    participant CD as «B» RedemptionConfirmDialog
    participant Gate as «C» PointsFeatureFlagGate
    participant Ctl as «C» RedemptionController
    participant BV as «C» ValidatePointsBalance
    participant LV as «C» EnforcePerUserRedemptionLimit
    participant Res as «C» ReserveInventory
    participant Disc as «C» ApplyDiscount
    participant Inv as «C» InventoryManager
    participant Iss as «C» IssueVoucher
    participant MI as «E» MarketplaceItem
    participant W as «E» Wallet
    participant PT as «E» PointTransaction
    participant R as «E» Redemption
    participant IC as «E» InventoryCounters ★new
    participant V as «E» Voucher

    P->>RD: viewReward(itemId)
    RD->>Ctl: getDetail(itemId)
    Ctl->>MI: getItem(itemId)
    MI-->>Ctl: pointCost, limits, rewardType
    Ctl-->>RD: RewardDetailViewModel
    RD-->>P: render(detail, "Redeem" CTA)

    P->>CD: confirmRedeem(itemId)
    CD->>Gate: gate(memberId)

    alt pointsFeatureFlag OFF
        Gate-->>CD: redemptionDisabled()
    else flag ON
        Gate->>Ctl: redeem(memberId, itemId)

        Ctl->>BV: validatePointsBalance(memberId, pointCost)
        BV->>W: getCurrentBalance(memberId)
        W-->>BV: currentBalance
        alt G4.1 currentBalance < pointCost
            BV-->>CD: INSUFFICIENT_BALANCE (prevent)  %% [G4.1]
        else sufficient
            Ctl->>LV: enforcePerUserLimit(memberId, itemId)
            LV->>R: countRedemptions(memberId, itemId, period)
            R-->>LV: usedCount
            alt G4.2 usedCount >= redemptionLimitPerUser
                LV-->>CD: LIMIT_REACHED (block)  %% [G4.2]
            else within per-user limit
                Ctl->>Res: reserve(itemId)
                Res->>Inv: reserveStock(itemId)
                Inv->>IC: reserve(itemId)
                IC->>IC: if remaining==0 → fail, else reserved += 1, remaining -= 1
                alt G4.3 stock remaining == 0 at confirm (under totalInventoryLimit)
                    IC-->>Inv: NO_STOCK
                    Inv-->>CD: OUT_OF_STOCK (block)  %% [G4.3]
                else reserved — COMMIT (atomic)
                    Ctl->>Disc: applyDiscount(item.rewardDiscountType, item.rewardDiscountAmount)
                    alt G4.4 rewardDiscountType == PERCENTAGE
                        Disc-->>Ctl: discountValue = amount%% of base  %% [G4.4]
                    else rewardDiscountType == CURRENCY_AMOUNT
                        Disc-->>Ctl: discountValue = amount in currency(ISO-4217)  %% [G4.4]
                    end

                    Ctl->>W: deduct(pointCost)
                    W->>W: currentBalance -= pointCost, lifetimeRedeemed += pointCost
                    Ctl->>PT: record(type=redeem, points=-pointCost, sourceRef=itemId)

                    Ctl->>Inv: issueReserved(itemId)
                    Inv->>IC: issue(itemId)
                    IC->>IC: reserved -= 1, issued += 1

                    Ctl->>Iss: issueVoucher(itemId, rewardType, discountValue)
                    Iss->>V: create(artifactType, code/QR, expiryDate=now+expiryRulesPostRedemption)
                    V-->>Iss: voucherId
                    Iss-->>Ctl: voucherId
                    Ctl->>R: persist(redemptionId, walletTxn=PT, item=MI, voucher=V, status=ISSUED)
                    Ctl-->>CD: REDEMPTION_OK(voucher, expiryDate)
                    CD-->>P: showArtifact(code/QR, valid-until expiryDate)
                end
            end
        end
    end
```

**Backward traceability (UC-G4)**

| Message | Robustness object | Use-case step |
|---|---|---|
| `gate` / `redemptionDisabled` | PointsFeatureFlagGate | G4 flag gate |
| `getDetail` / `getItem` | RedemptionController → MarketplaceItem | G4 basic |
| `validatePointsBalance` / `getCurrentBalance` / `INSUFFICIENT_BALANCE` | ValidatePointsBalance → Wallet | G4.1 |
| `enforcePerUserLimit` / `countRedemptions` / `LIMIT_REACHED` | EnforcePerUserRedemptionLimit → Redemption | G4.2 |
| `reserveStock` / `reserve` / `OUT_OF_STOCK` | ReserveInventory → InventoryManager → InventoryCounters (under totalInventoryLimit) | G4.3 |
| `applyDiscount(type, amount)` (PERCENTAGE vs CURRENCY_AMOUNT branch) | ApplyDiscount → MarketplaceItem.rewardDiscountType/Amount | G4.4 |
| `deduct` / `currentBalance -=` | Wallet (owns balance) | G4 commit |
| `record(type=redeem…)` | PointTransaction (owns ledger row) | G4 commit / audit |
| `issueReserved` / `issue` (reserved→issued) | InventoryManager → InventoryCounters | G4 commit |
| `issueVoucher` / `create(expiryDate=now+expiryRulesPostRedemption)` | IssueVoucher → Voucher (post-redemption expiry) | G4 commit |
| `persist(...)` | Redemption (links wallet txn, item, voucher) | G4 commit |

---

## UC-G5 — View "My Rewards" / Reward Artifact 🟢 P1

*Actor*: **Participant**. *Basic Course*: open My Rewards → list redemptions → load artifacts → evaluate usable-vs-expired per artifact → render list; on tap, open ArtifactViewer to render code/QR.
*Alternate Course*: G5.1 artifact expired or `used_flag` set → marked not usable.

```mermaid
sequenceDiagram
    autonumber
    actor P as Participant
    participant MR as «B» MyRewardsScreen
    participant AV as «B» ArtifactViewer (code/QR)
    participant Ctl as «C» MyRewardsController
    participant Exp as «C» ExpiryEvaluator
    participant R as «E» Redemption
    participant RA as «E» RewardArtifact ★new (Voucher)

    P->>MR: openMyRewards()
    MR->>Ctl: getMyRewards(memberId)

    Ctl->>R: listRedemptions(memberId)
    R-->>Ctl: [Redemption...]
    Ctl->>RA: getArtifacts(redemptionIds)
    RA-->>Ctl: [RewardArtifact...]

    loop per artifact
        Ctl->>Exp: evaluate(artifact)
        Exp->>RA: getExpiry_and_usedFlag(artifactId)
        RA-->>Exp: expiryDate, used_flag
        alt G5.1 expired OR used_flag == true
            Exp-->>Ctl: EXPIRED / USED (not usable)  %% [G5.1]
        else still valid
            Exp-->>Ctl: USABLE
        end
    end

    Ctl-->>MR: MyRewardsViewModel(usable, expired)
    MR-->>P: render(rewards with usable/expired state)

    P->>AV: openArtifact(artifactId)
    AV->>Ctl: getArtifactRender(artifactId)
    Ctl->>RA: getCodeOrQR(artifactId)
    RA-->>Ctl: code/QR payload
    Ctl-->>AV: ArtifactRenderModel
    AV-->>P: render(code/QR/confirmation)
```

**Backward traceability (UC-G5)**

| Message | Robustness object | Use-case step |
|---|---|---|
| `getMyRewards` / `listRedemptions` | MyRewardsController → Redemption | G5 basic |
| `getArtifacts` / `getCodeOrQR` | RewardArtifact/Voucher (owns code/QR) | G5 basic / viewer |
| `evaluate` / `getExpiry_and_usedFlag` / `EXPIRED/USED` | ExpiryEvaluator → RewardArtifact | G5.1 |

---

## UC-G6 — Configure Reward Catalog & Inventory 🟢 P1

*Actors*: **DoH Gamification Staff**, **ADHDS Operator** (same admin boundary). *Basic Course*: open admin console → submit item config (add/edit/remove) → validate cost/validity/limits → upsert MarketplaceItem under RewardCatalog → set inventory model (limited/unlimited) via InventoryRecord → confirm. All config-driven ("without development").
*Alternate Course*: validation failure (invalid cost/validity/limits) → reject, return errors.

```mermaid
sequenceDiagram
    autonumber
    actor Staff as DoH Gamification Staff
    actor Op as ADHDS Operator
    participant AC as «B» CatalogAdminConsole
    participant Ctl as «C» CatalogConfigController
    participant Val as «C» ItemConfigValidator
    participant Inv as «C» InventoryManager
    participant Cat as «E» RewardCatalog ★new
    participant MI as «E» MarketplaceItem
    participant IR as «E» InventoryRecord ★new

    alt Staff configures
        Staff->>AC: submitItemConfig(itemDraft)
    else Operator configures
        Op->>AC: submitItemConfig(itemDraft)
    end

    AC->>Ctl: applyConfig(itemDraft, action=add/edit/remove)

    Ctl->>Val: validate(itemDraft)
    Val-->>Ctl: validate cost/validity/limits
    alt validation failed
        Val-->>AC: CONFIG_INVALID(errors)  %% reject
    else valid
        Ctl->>Cat: upsertItem(itemDraft)
        Cat->>MI: save(name, desc, image, pointCost, validity, perUser/perPeriod limits)
        MI-->>Cat: itemId

        Ctl->>Inv: setInventoryModel(itemId, limited|unlimited, initialCount)
        Inv->>IR: initStock(itemId, count)
        Note over Inv,IR: G6.1 same InventoryManager does live decrement in UC-G4 (reuse)
        IR-->>Inv: ok

        Ctl-->>AC: CONFIG_SAVED(itemId)
        AC-->>Staff: confirm(saved)
        AC-->>Op: confirm(saved)
    end
```

**Backward traceability (UC-G6)**

| Message | Robustness object | Use-case step |
|---|---|---|
| `applyConfig` | CatalogConfigController | G6 basic |
| `validate` / `CONFIG_INVALID` | ItemConfigValidator | G6 validation |
| `upsertItem` / `save` | RewardCatalog → MarketplaceItem | G6 add/edit/remove |
| `setInventoryModel` / `initStock` | InventoryManager → InventoryRecord | G6.1 limited/unlimited + reuse in G4 |

---

## UC-G7 — Submit Reward 🟢 P1 *(added in marketplace supplement)*

*Actors*: **Reward Partner**, **DoH Gamification Staff** (intake). *Basic Course*: partner submits reward details (incl. **rewardDiscountType + rewardDiscountAmount** as two fields) and the **reward image** — for the **September Challenge** the image goes **manually to the Malaffi team** (offline, no upload UI) → record Partner (imageSubmissionMode=manualToMalaffi) → validate discount pair + config → hand off to catalog config (→ UC-G6) to upsert MarketplaceItem + init InventoryCounters.
*Alternate Courses*: G7.1 manual image path (Sept); G7.2 CMS upload (later increment, deferred); G7.3 discount type/amount not paired → reject.

```mermaid
sequenceDiagram
    autonumber
    actor Partner as Reward Partner
    actor Staff as DoH Gamification Staff
    participant SF as «B» RewardSubmissionForm
    participant MIS as «B» ManualImageSubmission→Malaffi (offline)
    participant Ctl as «C» PartnerRewardSubmissionController
    participant DV as «C» DiscountPairValidator
    participant Val as «C» ItemConfigValidator
    participant Cfg as «C» CatalogConfigController
    participant Inv as «C» InventoryManager
    participant P as «E» Partner ★new
    participant MI as «E» MarketplaceItem
    participant IC as «E» InventoryCounters ★new

    Partner->>SF: submitRewardDetails(draft)
    Staff->>SF: reviewIntake(draft)
    Partner->>MIS: handImageToMalaffi(image)  %% [G7.1] Sept: manual, no UI
    Note over MIS: CMS-managed upload is a later increment  %% [G7.2]

    SF->>Ctl: submitReward(draft, imageRef=manual/Malaffi)
    Ctl->>P: recordPartner(imageSubmissionMode=manualToMalaffi)

    Ctl->>DV: validateDiscountPair(rewardDiscountType, rewardDiscountAmount)
    alt G7.3 type set without amount (or vice-versa)
        DV-->>SF: DISCOUNT_PAIR_INVALID (reject)  %% [G7.3]
    else paired OK
        Ctl->>Val: validate(cost/validity/limits)
        Val-->>Ctl: ok
        Ctl->>Cfg: applyConfig(draft, action=add)
        Cfg->>MI: save(name, desc, image, pointCost, rewardDiscountType, rewardDiscountAmount, validity, limits, expiryRules)
        MI-->>Cfg: itemId
        Cfg->>Inv: setInventoryModel(itemId, totalInventoryLimit)
        Inv->>IC: initCounters(itemId, total, reserved=0, issued=0, remaining=total)
        IC-->>Inv: ok
        Cfg-->>SF: REWARD_SUBMITTED(itemId)
        SF-->>Partner: confirm(submitted)
        SF-->>Staff: confirm(submitted)
    end
```

**Backward traceability (UC-G7)**

| Message | Robustness object | Use-case step |
|---|---|---|
| `handImageToMalaffi` / Note CMS later | ManualImageSubmission→Malaffi boundary | G7.1, G7.2 |
| `submitReward` / `recordPartner` | PartnerRewardSubmissionController → Partner | G7 basic |
| `validateDiscountPair` / `DISCOUNT_PAIR_INVALID` | DiscountPairValidator → MarketplaceItem (rewardDiscountType/Amount) | G7.3 |
| `applyConfig` / `save` | CatalogConfigController → MarketplaceItem | G7 → G6 |
| `setInventoryModel` / `initCounters` | InventoryManager → InventoryCounters | G7 inventory |

---

## Cross-diagram traceability summary (sequence ⇄ robustness ⇄ use case)

| Use case | Boundary participants | Controllers→messages | Entities that own operations |
|---|---|---|---|
| UC-G1 | WeeklyFinalizedEvent | PointsFeatureFlagGate, RewardAccrualController, OncePerWeekGuard, WeeklyCapEnforcer, BonusPointsCrediter | WeeklyScore(getScoreValue), Wallet(credit), PointTransaction(record), SahatnaEvent/Screening(getEarnedPoints) |
| UC-G2 | WalletScreen | WalletViewController, TransactionHistoryAssembler | Member(resolveWallet), Wallet(getBalances), PointTransaction(listByWallet) |
| UC-G3 | MarketplaceCatalogScreen | PointsFeatureFlagGate, CatalogBrowseController, PointsNeededCalculator, InventoryManager | RewardCatalog/MarketplaceItem(listItems), Wallet(getCurrentBalance), InventoryRecord(getStock) |
| UC-G4 | RewardDetailScreen, RedemptionConfirmDialog | PointsFeatureFlagGate, RedemptionController, ValidatePointsBalance, EnforcePerUserRedemptionLimit, ReserveInventory, ApplyDiscount(type,amount), InventoryManager, IssueVoucher | MarketplaceItem(getItem/discount), Wallet(deduct), PointTransaction(record), Redemption(countRedemptions/persist), InventoryCounters(reserve/issue), Voucher(create+expiry) |
| UC-G5 | MyRewardsScreen, ArtifactViewer | MyRewardsController, ExpiryEvaluator | Redemption(listRedemptions), RewardArtifact(getExpiry/getCodeOrQR) |
| UC-G6 | CatalogAdminConsole | CatalogConfigController, ItemConfigValidator, InventoryManager | RewardCatalog/MarketplaceItem(upsert/save), InventoryRecord/InventoryCounters(initStock) |
| UC-G7 ★supp | RewardSubmissionForm, ManualImageSubmission→Malaffi (offline) | PartnerRewardSubmissionController, DiscountPairValidator, ItemConfigValidator, CatalogConfigController, InventoryManager | Partner(recordPartner), MarketplaceItem(save discount fields), InventoryCounters(initCounters) |

**Invariant check (sequence layer)**
- ✅ Each robustness **controller** appears either as a participant or as the message it owns; no behaviour leaked into entities — entity messages are data getters/mutators on their own attributes (Wallet balance, InventoryRecord stock, RewardArtifact expiry, PointTransaction ledger).
- ✅ Every robustness **alternate course** (G1.1–G1.4, G3.1, G4.1–G4.3, G5.1, G6 validation) appears as an `alt`/`opt` fragment.
- ✅ Actors message only boundaries; boundaries message only controllers; entities are reached only via controllers — ICONIX rules preserved into Step-3.
- ✅ Phase scope: all six use cases P1, feature-flag fragments retained on G1/G3/G4; no P2/P3 (Team/District/Title/baseline-goal) messages introduced.
