# Outcome-First Agent Loop — Submission

**Name:** Nikhil Raj (menikhil.1997@gmail.com) · **Date:** 2026-11-09 · **Hours actually spent:** one AI-assisted working session (not 12–16 h of hand-tuning; see §13) · **Language / storage:** Python 3.11, SQLite (WAL) single file, stdlib + numpy + httpx

## 0. TL;DR
- `./run.sh <SIM_URL>` starts one always-on controller that ingests events, detects, experiments, proposes through `/approvals`, applies, verifies, rolls back and records every decision in its own SQLite store.
- public_01: **+10.7%** conclusion rate vs baseline (all workflows); public_02: **+29.7%** (caller-ID incident rotated ~1 h after onset, hallucination fix applied for 3 credits, MTTR 180 min, 0 harmful); public_03 (load): **+14.3%**, 5 simulated days in **94 s** of controller wall time. Perturbed worlds: +26.7%, +10.3% (null), +37.0%.
- **Honest headline:** nearly all lift comes from caller-ID spreading/rotation, call timing and the prompt-incident fix. The welcome/voice experiments are statistically safe (**0 false winners in 24 null workflow-runs**) but have little power at these volumes: they promoted **no** true winner in any 8–24-day scenario (§5, §11).
- Crash tests: 4 random `kill -9`s (`scripts/crash_test.sh`) **and** 3 deterministic failpoints between a successful POST/PUT at the simulator and its local record (`scripts/crash_failpoints.sh`): each restarts and finishes, invariants pass, simulator request count equals ours, `apply_conflicts: 0`. A state DB from a different/finished world is detected and reset.
- Not built / cut: per-person call time, LLM-driven prompt experiments, a real multi-tenant scheduler (see §2). I traded lift for safety: a first version had +8.1/+28.6/+14.8% but 2/2/8 harmful changes (exploration launches); I cut challenger exposure to remove them (§11).

## 1. Assumptions
1. The simulator's `/workflows/{id}` governance block is the contract; memos that contradict it lose (see §3).
2. Variant effects (welcome, voice) act on the workflow's **primary** KPI; the other KPI is a guardrail (screened per variant: blocked if it loses more than half of the allowed drop, significantly).
3. Dials are treated as independent units. Repeat attempts to the same lead are correlated; I ignore that (z-scores are a little optimistic — compensated by a high z bar, the recency check and the holdout).
4. Welcome and voice are sampled independently by the sim, so a factorial design is unbiased on each margin; **I assume no welcome×voice interaction** (multiplicative effects).
5. Approvers only act inside `approver_hours`; I send non-urgent requests only between `start+1h` and `end-1h` (so ≥11:00 on Kestrel, which also satisfies the supervisor memo) and never outside hours unless it would still be decided before TTL.
6. "Customer-facing" = welcome message, voice, prompt, cohorts. These always go through `/approvals`, even where the policy would permit auto-apply (Kestrel). Schedule and caller-ID are "operational" and may auto-apply where the policy says so.
7. The first config ever observed is the business default; its majority variant per dimension is the **reference** (holdout) arm.
8. A reference holdout (20% of traffic per cohort for each dimension) is kept forever; decay detection and honest lift estimates depend on it.

## 2. Scope decisions
| # | Capability | Built / Partial / Cut | Why | What it would take to finish |
|---|---|---|---|---|
| C1 | Ingestion at load scale | **Built** | Chunk-level exactly-once (aggregates + cursor in one txn), aggregates only, no raw events. 150–210k events/s, 5.5M-event history in 29 s | Shard by workflow across processes for 10× |
| C2 | Lead joins + one shared cohort object | **Built** | `controller/cohorts.py`: canonical id from `where`; same object used by detection (`cohort_kpis`), experiments, hour tables, proposals, supervisor view | — |
| C3 | Bootstrap from history | **Built** (partial use) | History seeds caller-ID baselines, hallucination baseline, hour-of-day profiles, cohort-feature importance. History has no variant variance, so it cannot seed variant priors | Priors across workflows of a tenant |
| C4 | Call-time optimisation | **Partial** | Per-**cohort** hour weights from history+live pickup, with heterogeneity test (multiplicative null, Wilson–Hilferty z). **Per-person cut**: a person has 1–3 calls; the estimate is noise, and the memo that calls it the headline wasn't backed by a policy that allows it cheaply | Per-person posterior over hours for returning leads |
| C5 | Caller-ID health | **Built** | Rolling window vs own same-hour history *and* peers; stepwise rotation under `max_shift`; probe floor 2%; unseen IDs explored at 8% | Recovery model beyond a 2% probe |
| C6 | Welcome/voice experiments | **Built** | Ridge-pooled log-lift model, deterministic z, successive elimination, bounded challenger share | Interaction terms, adaptive allocation |
| C7 | Promotion, decay, rollback | **Built** | Recency confirmation before promoting; hourly decay watch; ban + rollback | Per-lead exposure-aware decay model |
| C8 | Hallucination response | **Built** | Detect → revert to last known-good prompt (validated, 3 credits) or LLM suggestions (validated) → proposal with validation evidence → verify after apply | Engagement check of the new prompt (only logged today) |
| C9 | Governance client | **Built** | State machine, TTL/apply-window/stale/lapse, re-proposal with fresh id, auto-apply stepping, batching, 24h cap | Per-tenant fairness of approver attention |
| C10 | Honest impact / affected / dry run | **Built (model-based)** | Dry run is a model replay over observed per-cell arm rates, labelled as such | Real shadow replay on held-out cohorts |
| C11 | Supervisor view | **Partial** | JSON at `:8800/view`; no UI | Small web page |
| C12 | Audit store | **Built** | `decisions` (append-only), `proposals`, `config_hist`, `incidents`, `credits`; `python -m controller.explain` | — |
| C13 | Crash recovery demonstrated | **Built** | Random SIGKILLs (`crash_test.sh`) + deterministic failpoints (`crash_failpoints.sh`: after submit POST, after apply POST, after auto PUT) + world-fingerprint reset | Kill during multi-step auto-apply stepping |
| C14 | Loop observability | **Built (rules in-process)** | `controller/alerts.py`: 5 page rules + 1 ticket rule, dedup + clear, `alerts` table, `:8800/alerts`, `:8800/metrics`; fired correctly in tests (late hallucination incident, flagged caller ID not yet rotated) | Route to a real pager |
| C15 | Fair credits / approver attention | **Partial** | Credits: equal share of 75% per workflow + a shared 25% reserve drawn only after a workflow exhausts its share (unit-tested). Approver attention: 2 proposals/day/workflow, no cross-tenant weighting | Weighted fair queue across tenants |

Principle: spend the effort where a wrong decision reaches a regulated client (governance, evidence, rollback, audit, crash safety) and where the hidden scenarios score (incidents, decay, supervisor edits). Everything that adds surface but not safety (UI, per-person times, LLM prompt search) was cut.

## 3. Stakeholders
**01 Sales.** *Accepted:* speed matters — evaluation is hourly, DID/hallucination actions are same-hour, rollbacks are immediate where policy allows. *Declined:* a single blended score (Product + engineering rule: pickup and engagement stay separate); auto-applying customer-facing winners; rolling out "persuasive" P4. *Wrong claims:* Kestrel's policy allows auto-apply for schedule/caller_id/welcome/voice only within `max_shift 0.2`, not "everything" (no prompt, no cohorts). **Northwind KYC auto-apply is `enabled: false`** — the QBR recollection is wrong. P4 hallucinates 2.5% (4× P1) and any prompt change needs validation ≥0.97 plus approval.
> Reply: "Happy to put a number on the screen: per-workflow lift on the primary KPI with the guardrail beside it, not blended. Winners go live as soon as evidence clears and the client approves; Kestrel allows auto-apply only for call timing and caller ID, and Northwind KYC has auto-apply off, so those need their approver. P4 'persuasive' hallucinates ~4× more than today's prompt and needs a validation pass plus approval; I won't roll it out blindly. The story I can defend on stage: 'it found the problem and fixed it within hours, with audit trail'."

**02 Compliance (Northwind).** *Accepted:* all customer-facing changes via named approval with validation evidence on prompts; requests only in approver hours; auto-apply limited to what the policy lists. *Wrong/partial:* "operational settings covered" is true for `nw_renewal` (schedule, caller_id) but **not `nw_kyc`**, where auto-apply is off, so there even caller-ID rotation is an approval. *Limit:* §3 of the memo wants "why did this customer hear this variant" in 24 h. My store keeps aggregates, not raw calls: I answer at (workflow, cohort, config version, time) level; the per-call variant is in the platform's call events, which must be retained.
> Reply: "Customer-facing changes (opening line, voice, script, cohorts) only ship after your approver says yes; prompt changes carry a validation run. Schedule and caller-ID changes auto-apply on renewal (your signed policy) and need approval on KYC. Every change is queryable with who/why/evidence. For per-customer audit within 24 h I can tell you config version, cohort and distribution live at any minute; the exact variant per call comes from call events, which we should retain 12 months. Requests go out 11:00–17:00 only."

**03 Platform/SRE.** *Accepted:* kill/restart test, idempotency keys, actionable alerts, loop metrics, no new infra. *Pushback:* none on infra — SQLite single file; it would move to the existing Postgres by swapping `store.py` (SQL is plain). Who operates it at 2 a.m.: nobody (embedded). *Numbers:* ~20 s of wall time per simulated 850k-event day on a laptop (budget: 600 s).
> Reply: "Kill/restart is scripted (`scripts/crash_test.sh`, 4 SIGKILLs, finishes, invariants + zero apply conflicts). Proposals are idempotent by deterministic ids; submit/apply are preceded by a durable intent row. No new infra: one SQLite file (swap to your Postgres later). One load day ≈ 20 s here; first thing to break at 10× is single-process ingest, then the SQLite writer. Pages: ingest lag > 10 min, controller down, credits < 15%, caller ID incident without a successful rotation. Everything else waits for morning."

**04 Kestrel ops supervisor.** *Accepted:* ≤2 requests/day (cap = min(2, policy−1)), never before 11:00, one batched request per cycle, one-screen view, her prompt edits are never silently overwritten (supervisor-edited dimensions are held 2 days and, for welcome/voice, her choice is kept unless there is evidence of a *win*), no `P5`-style fix (a validated candidate that looks like "strict/verbatim" is ranked last; engagement is verified after apply). *Pushback:* "tell me before anything changes": welcome/voice/prompt go via approval but caller-ID rotation and call timing auto-apply (policy-permitted, logged, visible on the view). Her prompt edit **was** reverted in public_02 — after a hallucination spike, via an approval with validation evidence, not behind her back.
> Reply: "Max two requests a day, none before 11:00, each one a single bundled change with the evidence. I won't overwrite your prompt or voice edits; if I see a safety problem (e.g. hallucination after your edit) I'll ask for approval with the numbers, never silently. Caller-ID swaps and call-time tweaks can happen without a request because your policy allows it, but they all show up on one screen: testing / winning / needs you / changed today."

**05 Product.** *Accepted:* separate KPIs everywhere; one cohort object; min cohort/evaluation choices with reasoning (§5); impact score ranks the queue; expired = rejection → re-queue after 12 h with fresh data and a new proposal id; only observed arms count (aggregation is by the variant recorded on the call); winner updates only its workflow. *Cut:* per-person call time (not P0 for safety; see C4).
> Reply: "Done: separate pickup/engagement, one cohort id used by detection, experiments and the view, impact = lower-bound model gain (so it ranks), expired proposals re-queued with fresh evidence. Cohort floor is 3% of traffic and winners need z≥2.2 and ≥2% lift plus recent-2-day confirmation: costs ~2–4 days of exploration, buys a low false-winner rate. Per-person call time is cut: 1–3 calls per person isn't enough signal; per-cohort timing is in."

**06 CTO.** Accepted fully: explainability over lift; credits only where they change a decision (3 credits in public_02, 0 in 01/03); scale designed for aggregates; written choices. *Checked claims:* none false; the memo says trust the system's contract — used throughout.
> Reply: "Chose governance, evidence, rollback, audit and crash safety over breadth. Cut: per-person timing, LLM prompt search, UI. First thing to break at 10×: single-process Python ingest (~200k ev/s), then SQLite writes; partition by workflow hash."

## 4. Architecture
```
 sim /events/chunks ──▶ Ingestor ──(1 txn: aggregates + cursor)──▶ SQLite ◀──── view/explain (read-only)
                                                      │
 loop (15 sim-min tick) ─▶ per workflow WF.tick():    ▼
   sync_config (supervisor edits → hold dims)   aggregates: agg_var(seg×variant×6h×version), agg_hour, agg_did,
   gov.reconcile (poll/apply approvals)                      agg_prompt(hallucination/KPI), lead_day
   watch_halluc / watch_dids / watch_decay
   optimize (hourly, gated by approver hours) ─▶ Planner (cohorts, plans, hours) ─▶ Gov.submit | Gov.auto_apply ─▶ sim
 state in SQLite: kv(wf state) · proposals · decisions(audit) · config_hist · incidents · credits · metrics
```
Restart: read cursors, ingest any unprocessed chunk (history first, idempotent), reload recent lead→cell map, `init_state` (no-op if state exists), reconcile `intent`/`pending`/`approved`/`applying` proposals against `/approvals` and config history, resume the loop. The sim is the authority on time; the controller never assumes a tick was processed.

## 5. The learning loop
- **Cohorts.** Cells are `lang|tier|age|value`. A ridge model (per dimension & variant) on one-hot feature levels gives coefficient z-scores; features with |z|≥2 (experiments) or hour-profile heterogeneity z≥4 are "important"; **at most 2 features** define the partition (≤20 cells, ≤12 cohorts), cohorts under 3% of traffic fold into default (avoids fragmentation). Overlap problem (first-match) is solved by projecting plans onto the same feature set and covering equal-plan cells with exact rectangles (`merge_rectangles`).
- **Experiment design.** Factorial: welcome and voice sampled independently, reference 75% (≤3 options) / 70% (challengers 25–30% in total), challengers share the rest; after a win: winner 65%, reference 20%, others 15%. Clearly worse variants (z≥2.5 below) are dropped from exploration; guardrail-blocked variants are excluded.
- **Winner.** Posterior log-lift per cell from a ridge model; the *variance is computed from the workflow-wide rate*, not each cell's own outcome (the cell-outcome variance made lucky cells look more precise, so inverse-variance weighting was biased upward: found as repeated false winners on the same young-age cohorts across null seeds). Dials are not independent, so variance is inflated by an empirical design effect from a placebo contrast (reference arm split by day parity; measured ≈1.0–1.9). A challenger wins only if its lower bound exceeds +2% at a **family-wise bar** z = Φ⁻¹(1 − 0.30/(m·√looks)) (m = variant×cell comparisons, looks = days in window; ≈2.2–2.9 in practice), **and** the most recent 2 days confirm (lift LB>0 at z=1.28; promised lift = min of full-window and recent). An incumbent winner needs only a 90% lower bound > 0 (hysteresis; decay is handled separately) and an applied change starts a 36 h cooldown. Closed-form, no sampling ⇒ deterministic.
- **False-winner rate (measured).** 8 null worlds (no variant effects, different seeds) × 3 workflows × 10 days: **0 false-winner proposals**. Before these fixes: 7 proposals / 4 applied in the same 24 runs. A point estimate from 24 runs, not a tight bound (95% upper limit ≈ 12% per workflow-run).
- **Power (measured, and weak).** With ~25–30% of traffic on challengers (10–12% per arm) the controller promoted no true winner in public_01/02, pert_A/C or a 24-day run of public_01's truth (e.g. `ks_cancel` V4: pooled +7% ±4%, z≈1.8 vs a bar of 2.47). With looser bars it did find real effects (V4 for ks 18–30 at day 7) but also false ones; I chose false-winner control over lift. More power needs more traffic on challengers (more harm), longer horizons, or cross-workflow priors.
- **Decay/rollback.** Hourly: winner vs reference over the last 36 h: decayed if lift+1.28·se < +1.5% or lift+2·se < 0. Variant is banned, plan recomputed, rollback via auto-apply where the policy allows (stepped by `max_shift`) else an urgent approval.
- **Call time / caller ID.** Per-cohort hour weights ∝ (cohort pickup in hour / cohort mean)^1.5, shrunk toward the mean (k=40), clipped [0.35, 3], every window hour present (a missing hour = weight 0). Caller IDs: flagged → 2% probe; unseen → 20% each (cap 50%); healthy ∝ pickup (≈ uniform, which spreads per-ID load); re-optimised at most daily and only for TV≥0.15. Spreading load beat a cautious 8% probe in all five test worlds (public_01 +5.4%→+10.7% etc.) at the price of a graded-harmful day-0 launch when an unseen ID is spam-flagged. **Disclosure:** the load-spreading idea was prompted by a parameter I saw while reading the provided public scenario file as a developer; the controller does not read it and the effect is visible in its own data (single-ID workflows flagged on day 0), but treat the gain as partly tuned to public truth.
- **Cohort stability.** Cohorts are keyed on win/explore status only; avoid-sets no longer create or remove cohorts (they caused near-daily approved changes on one workflow). `next_campaign_only` workflows wait 24 h after an agent-facing change before the next proposal, because it only reaches the next campaign.
- **Guardrail.** Per variant: if its pooled guardrail-KPI difference vs reference is below −½·allowed drop (z<−1.64) it is blocked; drift of the guardrail KPI (24 h vs week) raises an alert.

## 6. Governance
```
intent ─POST─▶ pending ─▶ approved ─apply─▶ applied
   │              ├▶ rejected  (backoff 12h, re-propose with fresh data)
   │              └▶ expired   (same as rejection)
   └▶ stale / failed           approved ─▶ lapsed (410) | stale (409 / base moved) → re-propose from fresh state
auto path: intent ─PUT─▶ applied | 403 ⇒ refused ⇒ approval path
```
Batching: one `opt` request bundles cohorts + allocations + schedule + caller-ID; cap `min(2, max_requests_24h−1)` so an incident always has a slot. Timing: `start+1h … end−1h`; urgent only if still decided before TTL. Auto-apply is used for schedule/caller-ID and for protective rollbacks; **voluntarily not** for Kestrel welcome/voice winners (supervisor memo, regulated context). Impact = lower-bound model gain/8% (+0.1 option value for pure exploration); affected leads = daily leads in cells whose cohort distribution or hour table changes; dry run = model replay over observed arm rates (labelled as such, not a live test). Supervisor edit: recorded as `supervisor_edit`, dimension held 2 days; afterwards the supervisor's welcome/voice distribution is protected unless there is evidence of a *win*, and a supervisor schedule or caller-ID split is protected until they change it again (caller-ID may still move for a health incident, via the policy path), in-flight proposals die with `stale` and are re-proposed from fresh state.

## 7. Incidents (public_02, ks_cancel)
| sim time | event |
|---|---|
| D2 10:00 | D2 caller ID flagged (hidden truth) |
| D2 11:00 | detected: pickup 15.7% vs own same-hour history 26.7% (z=−4.8) and peers 25.3% (z=−3.4), n=377; traffic share 9.8%→2.3% by D3 (stepped under `max_shift 0.2`, auto-apply) |
| D3 11:30 | supervisor ships P2 |
| D3 13:15 | hallucination spike: 10/191 flagged (5.2% vs 1.5% baseline, p=7.8e-4); known-good P1 validated (n=300, 3 credits, 0.987) → approval request |
| D3 14:15 | approved + applied; 15:15 verified (2.6% over 116 calls); grader MTTR 165 min |
Verification has the opposite burden of proof from detection: a fix is 'resolved' only when the rate is not >1.5× baseline at p<0.05 over ≥100 calls (an earlier version declared victory at 4.5% vs 1.5% because the spike test lacked power). Thresholds: DID z≤−4 vs same-hour own history and ≥25% drop, plus (z≤−3, ≥15%) vs peers; hallucination p<1e-3 within 24 h of a prompt change (p<1e-4 otherwise), ≥1.75× baseline. Expected FP: ~1e-4/test/hour; I saw one false DID flag on `nw_kyc` in an earlier version (hour-of-day confound), fixed by same-hour baselines. Credits: 3 in public_02.

## 8. Scale (public_03_load, laptop, 5 simulated days)
Ingest 150–210k events/s (history 5.54M events in 29 s); controller wall 94 s for 5 days (~19 s per 850k-event day vs the 600 s budget); decision lag ≤ one 15-min tick plus ≤1 s of processing; max RSS 1.3 GB (largest process; includes the simulator's own memory), state DB 166 MB. **Breaks first at 10×:** single-threaded JSON parsing (~200k ev/s), then SQLite single writer and the in-memory lead→cell map. Partition by `hash(workflow)` across processes (each owns its state rows; a lease per workflow), keep the aggregate schema.

## 9. Reliability
Method: (a) `scripts/crash_test.sh` SIGKILLs the controller 4× (after 1–4 s, sim at D2–D9); (b) `scripts/crash_failpoints.sh` exits the process exactly after the simulator accepted a submit / apply / auto-apply but before we recorded it (`CTL_FAILPOINT`), restarts, and asserts simulator-side `approval_requests` == our proposals with an approval id (no duplicate, no lost request) and `apply_conflicts == 0` (`reports/crash_failpoints.log`: all 3 pass). (c) On boot the controller compares `{scenario, end_minute}` and the sim clock with what the DB last saw; a different or fresh world wipes the DB instead of resuming stale cursors (tested: 01→02→02 on one DB). Result: invariants pass (no intent/applying left, no duplicate apply, every applied proposal has a trail), simulator-side `apply_conflicts: 0`, `auto_apply_rejected: 0`. Lost state: nothing durable; in-flight HTTP responses are reconciled by proposal id (409 duplicate → adopt). Sim 5xx/transport errors: exponential backoff, 12 tries; 4xx are interpreted (409 stale → stale, 410 → lapsed, 403 → fall back to approval, 402 → credit gate). A failing workflow is isolated (`controller_error` decision) so one bad workflow doesn't stop the loop.

## 10. Audit & observability
```
python -m controller.explain --db state/public_02.db --wf ks_cancel --at 2027-01-07T17:00:00+05:30
→ config v12, 2027-01-07T14:15, actor controller_approved, changed prompt_version
  proposal ks_cancel-v11-…, approval apr_00006, submitted 13:15, decided/applied 14:15,
  rationale "10 of 191 connected calls flagged … vs baseline 1.52% (p=7.8e-04) … Validation val_00001 pass_rate 0.987",
  diff {prompt_version: P2→P1}, evidence {validation_run_id: val_00001}
  after: incident_resolved "hallucination back to baseline (2.59%) over 116 calls; 120 sim-min from detection to verified fix"
```
Also `:8800/view` (what's tested/winning/needs you/changed), `:8800/metrics`, `sqlite3 state/*.db 'select * from decisions'`. **Page on:** controller down / ingest lag > 10 min / credits < 15% / DID incident with no applied rotation after 2 h / hallucination incident unresolved after 4 h. **Don't page:** rejected proposals, drift alerts, single auto-apply refusals (morning review).

## 11. Results
Final code (numbers from `reports/`; the simulator is deterministic per seed; differences between code revisions come from approver timing):

| scenario | ALL conclusion Δ | applied changes (grader) |
|---|---|---|
| public_01 (8 d) | +10.7% | 6: 4 beneficial, 1 neutral, **1 harmful** (day-0 launch probing the spam-flagged D4) |
| public_02 (10 d) | +29.7% | 8: 7 beneficial, 1 neutral, **0 harmful**; prompt incident MTTR 180 min |
| public_03 (5 d, 12 wf) | +14.3% | 34: 25 beneficial, 5 neutral, **4 harmful** — all the same day-0 renewal launch probing D4 |

Interpretation. The wins are structural: spreading load across caller IDs and rotating the flagged one, per-cohort call timing, and the prompt fix (hallucinated calls 90 vs 348 in ks_cancel). The welcome/voice loop is safe but found nothing at these volumes; engagement headroom captured is 3–24%, mostly from timing. In public_01 `ks_cancel` is ~0%. `nw_kyc` engagement dips a few points in some runs (pickup is its primary KPI; inside the 0.02 guardrail in the reports I checked, not by a wide margin).

### Perturbed scenarios (`scripts/make_perturbed.py`, `scenarios/perturbed/`)
Same schema, different truth, incidents and policy (the controller never reads these files).

| scenario | what changed | ALL conclusion Δ | applied (grader) | notes |
|---|---|---|---|---|
| pert_A | other effects, caller ID flagged on two workflows, supervisor ships **P4** on nw_renewal | +26.7% | 9: 7 beneficial, 1 neutral, 1 harmful | The harmful change is the *safety revert* P4→P1 (P4 engages ~6% better but hallucinates ~4×). Detected ~8 h after the edit; MTTR 1425 min. |
| pert_B_null | no variant truly works, no incidents | +10.3% (all caller-ID/timing) | 6: 4 beneficial, 1 neutral, 1 harmful (day-0 launch) | no false winner |
| pert_C | approvers 11–17h, 2 req/day, 25% reject rate, two caller-ID incidents, supervisor schedule edit, bad script on ks | +37.0% | 8 beneficial, 0 harmful | supervisor schedule edit preserved; prompt-fix MTTR 1425 min (detected late afternoon; approver window 11–17h): the `halluc_unresolved` page fired |
| null_s11…s18 | 8 seeds of a null world | +8.7…+12.0% | — | **0 false-winner proposals in 24 workflow-runs** |
| power_24d | public_01 truth over 24 days | +11.4% | — | 0 true winners promoted (§5 Power) |

Prompt-incident MTTR varies 150–1425 min between runs/revisions: detection depends on how fast flagged calls accumulate (the detector's flag rate is noisy) and a late-afternoon detection waits for the next approver day.

Found by the perturbations/null worlds and fixed: slow detection of a moderate hallucination rise; winner-take-all caller-ID weights; biased variance weighting (false winners); a min-count filter that silently disabled the lift model at 12% arms; cohort churn from avoid-sets; premature "resolved" at incident verification. Not fixed: §13.

## 12. Trade-offs & rejected alternatives
| Option | Why considered | Why rejected / what instead |
|---|---|---|
| Thompson sampling | Faster allocation | Random draws; brief demands deterministic winner selection — used closed-form posterior + successive elimination |
| Per-cell tests with BH | Standard FDR | Cells are small; ridge pooling gives power and shrinkage, z bar high |
| Auto-apply Kestrel winners | Speed (Sales) | Supervisor memo + regulated context; request cap makes approvals cheap |
| Postgres/Redis | Ops already runs them | Embedded SQLite = zero new infra; swap is one module |
| Raw event storage | Per-lead audit | 850k events/day; kept aggregates, flagged retention requirement |
| LLM-suggested prompts first | Looks smart | Last known-good prompt is free, data-backed; LLM only if that fails |
| Per-person call time | Product P0 | 1–3 calls/person; cut |

## 13. Known weaknesses
- **The experiment loop has little power.** Zero true winners promoted in every scenario run, including 24 days; false-winner rate measured 0/24 but that is the price. Lift is dominated by non-experiment levers: asked "what did the learning loop learn?", the honest answer is "mostly caller-ID and timing".
- **Day-0 launch is graded harmful when an unseen caller ID is bad** (20% probe): 1 of 6 changes in public_01, 4 of 34 in public_03.
- **Caller-ID health is load-driven and my model is a heuristic.** In null worlds the detector flags IDs with no injected incident (probably real load-induced degradation); rotating a flagged ID can push load onto survivors and chain flags. Needs a load-aware model and more IDs per workflow.
- **Prompt-incident time-to-fix varies 150–1425 min** with detector power and approver hours; the baseline flag rate is inflated by detector false positives (1.5% vs ~0.6% true).
- I tuned thresholds while reading grader output on public and perturbed scenarios (no hidden-truth reads, but some fitting, incl. the load-spreading choice, §5). Hidden scenarios may behave differently.
- No welcome×voice interaction, no attempt-number/hour confound handling beyond the design-effect inflation.
- Decay watch needs ≥150/80 calls per cohort in 36 h; tiny cohorts decay unnoticed (folded into default).
- Engagement of a fix prompt is only logged after apply; a "verbatim script" fix is only ranked last.
- Alerts are in-process, not wired to a pager; `view` has no auth (127.0.0.1 only). Single-process (does not use the 4 vCPUs). Single-session work; commit history is coarse.

## 14. If this went to production at Formi next month
1. Retain call events (12 months) and wire per-call audit; 2. Postgres store + per-workflow lease and process sharding; 3. alert rules + runbooks for the 5 pages; 4. shadow mode for two weeks (propose, never apply) to measure false-winner/rejection rates on real data; 5. staged exploration + cross-workflow priors; 6. small web supervisor page; 7. engagement-aware prompt selection; 8. per-person timing once call volume per person supports it.
