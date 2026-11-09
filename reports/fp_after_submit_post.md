# Grade report — public_02_incidents

## Outcomes vs baseline (no-op controller)

| workflow | conclusion rate | Δ | pickup | Δ | engagement | Δ | engagement gap captured | hallucinated calls (base) |
|---|---|---|---|---|---|---|---|---|
| ks_cancel | 0.364 | +54.6% | 0.247 | +36.3% | 0.504 | +7.8% | 35% | 98 (348) |
| nw_kyc | 0.470 | +25.6% | 0.292 | +24.4% | 0.603 | -0.9% | 0% | 29 (29) |
| nw_renewal | 0.464 | +7.2% | 0.283 | +8.1% | 0.550 | -0.8% | 6% | 60 (54) |
| ALL | 0.420 | +27.0% | 0.268 | +22.2% | 0.542 | +1.7% | 21% | 187 (431) |

## Changes applied by the controller

18 applied — neutral: 5, beneficial: 12, harmful: 1

- ks_cancel v2 (controller_approved) dims=['welcome_message', 'voice', 'schedule'] engageΔ=+0.009 didΔ=+0.000 → **neutral**
- nw_renewal v2 (controller_approved) dims=['welcome_message', 'voice', 'caller_id', 'schedule'] engageΔ=+0.015 didΔ=+0.026 → **beneficial**
- nw_kyc v2 (controller_approved) dims=['caller_id', 'schedule'] engageΔ=+0.000 didΔ=+0.086 → **beneficial**
- nw_renewal v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.054 → **beneficial**
- ks_cancel v3 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.179 → **beneficial**
- ks_cancel v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.152 → **beneficial**
- ks_cancel v5 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.088 → **beneficial**
- ks_cancel v6 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.036 → **beneficial**
- ks_cancel v7 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.036 → **beneficial**
- ks_cancel v8 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.035 → **beneficial**
- ks_cancel v9 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.026 → **beneficial**
- ks_cancel v10 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=-0.025 → **harmful**
- nw_renewal v4 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.004 → **neutral**
- nw_kyc v3 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.268 → **beneficial**
- ks_cancel v12 (controller_approved) dims=['prompt_version'] engageΔ=+0.102 didΔ=+0.000 → **beneficial**
- ks_cancel v13 (controller_auto) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.011 → **neutral**
- nw_kyc v4 (controller_approved) dims=['caller_id'] engageΔ=+0.000 didΔ=+0.004 → **neutral**
- nw_renewal v6 (controller_approved) dims=['cohorts', 'welcome_message', 'schedule'] engageΔ=-0.001 didΔ=+0.000 → **neutral**

## Governance

```
{
  "approval_requests": 8,
  "decisions": {
    "approved": 7,
    "rejected": 1,
    "expired": 0
  },
  "rejection_reasons": {
    "approver declined (judgement call)": 1
  },
  "applied_via_approval": 7,
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
      "2": 0.1,
      "3": 0.021,
      "4": 0.018,
      "5": 0.02,
      "6": 0.019,
      "7": 0.018,
      "8": 0.022,
      "9": 0.021
    }
  },
  {
    "type": "supervisor_edit",
    "workflow": "ks_cancel",
    "at": "D3 11:30",
    "mttr_minutes": 255,
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
    "2": 0.15,
    "3": 0.122,
    "4": 0.125,
    "5": 0.138,
    "6": 0.134,
    "7": 0.129,
    "8": 0.113,
    "9": 0.128
  }
}
```

Credits used: 3 · validation runs: 1 · LLM fix calls: 0