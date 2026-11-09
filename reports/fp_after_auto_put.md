# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.358 | +51.9% | 0.247 | +36.2% | 0.497 | +6.4% | 34% | 96 (348) |
| nw_kyc | 0.441 | +18.0% | 0.282 | +20.2% | 0.591 | -2.8% | 0% | 40 (29) |
| nw_renewal | 0.474 | +9.6% | 0.287 | +9.3% | 0.554 | -0.2% | 6% | 67 (54) |
| ALL | 0.414 | +25.3% | 0.267 | +21.8% | 0.537 | +0.9% | 21% | 203 (431) |

## Changes applied by the controller

17 applied — neutral: 6, beneficial: 11

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.009 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.015 didΔ=+0.026 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.086 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.054 → **beneficial**
- ks_cancel v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.179 → **beneficial**
- ks_cancel v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.152 → **beneficial**
- ks_cancel v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.088 → **beneficial**
- ks_cancel v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.033 → **beneficial**
- ks_cancel v7 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.032 → **beneficial**
- ks_cancel v8 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.031 → **beneficial**
- ks_cancel v9 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.018 → **neutral**
- ks_cancel v10 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.013 → **neutral**
- nw_renewal v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.003 → **neutral**
- ks_cancel v12 (controller_approved) dims=['prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.275 → **beneficial**
- ks_cancel v13 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.013 → **neutral**
- nw_kyc v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.003 → **neutral**

## Governance

```
{
  "approval_requests": 8,
  "decisions": {
    "approved": 6,
    "rejected": 2,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 2
  },
  "applied_via_approval": 6,
  "auto_applied": 11,
  "auto_apply_rejected": 0,
  "apply_conflicts": 0,
  "lapsed": 0,
  "peak_requests_per_24h": {
    "nw_renewal": 1,
    "nw_kyc": 1,
    "ks_cancel": 1
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
      "2": 0.115,
      "3": 0.017,
      "4": 0.022,
      "5": 0.018,
      "6": 0.022,
      "7": 0.02,
      "8": 0.021,
      "9": 0.02
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D3 11:30",
    "mttr_minutes": 390,
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
    "2": 0.118,
    "3": 0.131,
    "4": 0.128,
    "5": 0.122,
    "6": 0.125,
    "7": 0.124,
    "8": 0.126,
    "9": 0.127
  }
}
```

Credits used: 3 · validation runs: 1 · LLM fix calls: 0