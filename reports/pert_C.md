# Grade report — pert_C

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.351 | +50.9% | 0.246 | +41.6% | 0.491 | +3.7% | 40% | 97 (241) |
| nw_kyc | 0.474 | +23.6% | 0.298 | +21.6% | 0.599 | +0.0% | 0% | 40 (18) |
| nw_renewal | 0.454 | +33.6% | 0.279 | +30.7% | 0.543 | -0.4% | 7% | 73 (45) |
| ALL | 0.412 | +37.0% | 0.267 | +32.9% | 0.533 | +0.7% | 15% | 210 (304) |

## Changes applied by the controller

8 applied — beneficial: 8

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.002 didΔ=+0.033 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.190 → **beneficial**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.012 didΔ=+0.068 → **beneficial**
- ks_cancel v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.177 → **beneficial**
- ks_cancel v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.151 → **beneficial**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.110 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.212 → **beneficial**
- ks_cancel v6 (controller_approved) dims=['prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**

## Governance

```
{
  "approval_requests": 6,
  "decisions": {
    "approved": 5,
    "expired": 1
  },
  "rejection_reasons": {},
  "applied_via_approval": 5,
  "auto_applied": 3,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "nw_renewal": 1,
    "nw_kyc": 1,
    "ks_cancel": 2
  }
}
```

## Incidents

```
[
  {
    "type": "did_flagged",
    "workflow": "ks_cancel",
    "at": "D1 11:00",
    "flagged_did_share_by_day": {
      "1": 0.132,
      "2": 0.029,
      "3": 0.027,
      "4": 0.026,
      "5": 0.02,
      "6": 0.028,
      "7": 0.027,
      "8": 0.026,
      "9": 0.028
    }
  },
  {
    "type": "did_flagged",
    "workflow": "nw_renewal",
    "at": "D3 15:00",
    "flagged_did_share_by_day": {
      "3": 0.207,
      "4": 0.021,
      "5": 0.021,
      "6": 0.019,
      "7": 0.022,
      "8": 0.02,
      "9": 0.022
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "nw_renewal",
    "at": "D4 12:00"
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D5 11:30",
    "mttr_minutes": 1425,
    "fixed_by": "controller_approved"
  }
]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{}
```

Credits used: 6 · validation runs: 2 · LLM fix calls: 0