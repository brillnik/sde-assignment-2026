# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.352 | +49.4% | 0.242 | +33.4% | 0.499 | +6.7% | 35% | 90 (348) |
| nw_kyc | 0.451 | +20.6% | 0.288 | +22.9% | 0.591 | -2.9% | 0% | 26 (29) |
| nw_renewal | 0.481 | +11.0% | 0.291 | +10.8% | 0.552 | -0.5% | 5% | 63 (54) |
| ALL | 0.416 | +25.8% | 0.268 | +21.9% | 0.538 | +1.0% | 21% | 179 (431) |

## Changes applied by the controller

20 applied — neutral: 9, beneficial: 11

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.009 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.015 didΔ=+0.026 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.086 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.054 → **beneficial**
- ks_cancel v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.179 → **beneficial**
- ks_cancel v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.152 → **beneficial**
- ks_cancel v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.088 → **beneficial**
- ks_cancel v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.031 → **beneficial**
- ks_cancel v7 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.031 → **beneficial**
- ks_cancel v8 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.030 → **beneficial**
- nw_renewal v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.004 → **neutral**
- ks_cancel v10 (controller_approved) dims=['prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.262 → **beneficial**
- ks_cancel v11 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.010 → **neutral**
- nw_renewal v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.002 → **neutral**
- ks_cancel v12 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.002 → **neutral**
- ks_cancel v13 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.002 → **neutral**
- ks_cancel v14 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.000 → **neutral**
- ks_cancel v15 (controller_approved) dims=['cohorts', 'voice', 'schedule'] engageΔ=-0.001 didΔ=+0.000 → **neutral**
- ks_cancel v16 (controller_approved) dims=['cohorts', 'voice', 'schedule'] engageΔ=+0.001 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 9,
  "decisions": {
    "approved": 7,
    "rejected": 2,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 2
  },
  "applied_via_approval": 7,
  "auto_applied": 13,
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
    "at": "D2 10:00",
    "flagged_did_share_by_day": {
      "2": 0.102,
      "3": 0.018,
      "4": 0.019,
      "5": 0.018,
      "6": 0.018,
      "7": 0.021,
      "8": 0.021,
      "9": 0.022
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D3 11:30",
    "mttr_minutes": 240,
    "fixed_by": "controller_approved"
  },
  {
    "type": "supervisor_edit",
    "workflow": "nw_renewal",
    "at": "D5 15:00"
  }
]
```

## Decaying variants — share of in-population calls still on the variant, by day after onset

```
{
  "nw_renewal:welcome_message=W3": {
    "2": 0.122,
    "3": 0.122,
    "4": 0.129,
    "5": 0.128,
    "6": 0.131,
    "7": 0.133,
    "8": 0.133,
    "9": 0.135
  }
}
```

Credits used: 3 · validation runs: 1 · LLM fix calls: 0